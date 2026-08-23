"""Pure, DB-free derivation of a product's next release version.

Product versions are server-owned (see ``docs/design/API_CONTRACT.md`` §5): a
cut applies the default bump — **minor** — to the product's current version,
which is either the version of its latest release or, when it has never been
released, its configured ``base_version``. These helpers are pure so the cut
lane can unit-test the arithmetic without a database.
"""

from app.models.enums.bump_level import BumpLevel

_SEPARATOR = "."
_PRERELEASE_SEPARATOR = "-"
_CORE_PART_COUNT = 3


def _parse_core(version: str) -> tuple[int, int, int]:
    """Parse the ``major.minor.patch`` core of a semver string.

    Any ``-prerelease`` suffix is discarded: a minor bump zeroes the patch and
    drops the prerelease, so only the numeric core is needed.

    Args:
        version: A version string such as ``"5.1.0"`` or ``"5.1.0-rc.1"``.

    Returns:
        The ``(major, minor, patch)`` triple.

    Raises:
        ValueError: When the core is not three dot-separated non-negative
            integers.
    """
    core = version.split(_PRERELEASE_SEPARATOR, 1)[0]
    parts = core.split(_SEPARATOR)
    if len(parts) != _CORE_PART_COUNT:
        raise ValueError(f"Version '{version}' is not in major.minor.patch form.")
    try:
        major, minor, patch = (int(part) for part in parts)
    except ValueError as error:
        raise ValueError(f"Version '{version}' has non-integer components.") from error
    if major < 0 or minor < 0 or patch < 0:
        raise ValueError(f"Version '{version}' has negative components.")
    return major, minor, patch


def bump_minor(version: str) -> str:
    """Return ``version`` with its minor component incremented and patch reset.

    ``X.Y.Z`` (with any prerelease suffix) becomes ``X.(Y+1).0``.

    Args:
        version: The current version string.

    Returns:
        The minor-bumped version string.

    Raises:
        ValueError: When ``version`` is not a valid ``major.minor.patch`` core.
    """
    major, minor, _patch = _parse_core(version)
    return f"{major}{_SEPARATOR}{minor + 1}{_SEPARATOR}0"


def bump_major(version: str) -> str:
    """Return ``version`` with its major component incremented and the rest reset.

    ``X.Y.Z`` (with any prerelease suffix) becomes ``(X+1).0.0``.

    Args:
        version: The current version string.

    Returns:
        The major-bumped version string.

    Raises:
        ValueError: When ``version`` is not a valid ``major.minor.patch`` core.
    """
    major, _minor, _patch = _parse_core(version)
    return f"{major + 1}{_SEPARATOR}0{_SEPARATOR}0"


def bump_patch(version: str) -> str:
    """Return ``version`` with its patch component incremented.

    ``X.Y.Z`` (with any prerelease suffix) becomes ``X.Y.(Z+1)``; the prerelease
    is dropped, matching the minor/major bumps.

    Args:
        version: The current version string.

    Returns:
        The patch-bumped version string.

    Raises:
        ValueError: When ``version`` is not a valid ``major.minor.patch`` core.
    """
    major, minor, patch = _parse_core(version)
    return f"{major}{_SEPARATOR}{minor}{_SEPARATOR}{patch + 1}"


def apply_bump(current: str, level: BumpLevel) -> str:
    """Apply a derived bump ``level`` to ``current``.

    ``MAJOR``/``MINOR``/``PATCH`` bump the respective component (dropping any
    prerelease); ``NONE`` leaves the version string unchanged — a zero-change
    re-cut carries the same product version (G-P9d).

    Args:
        current: The product's current version (its latest release version, or
            its configured ``base_version`` when it has never been released).
        level: The derived product bump.

    Returns:
        The server-assigned ``product_version`` for the new release.

    Raises:
        ValueError: When ``current`` is not a valid ``major.minor.patch`` core.
    """
    if level is BumpLevel.MAJOR:
        return bump_major(current)
    if level is BumpLevel.MINOR:
        return bump_minor(current)
    if level is BumpLevel.PATCH:
        return bump_patch(current)
    return current


def next_product_version(latest_release_version: str | None, base_version: str) -> str:
    """Compute the product version a new cut should carry.

    The current version is the product's ``latest_release_version`` when it has
    releases, otherwise its configured ``base_version``. The default bump
    (minor) is applied to that current version.

    Args:
        latest_release_version: The ``product_version`` of the product's most
            recent release, or ``None`` when it has never been released.
        base_version: The product's configured starting version.

    Returns:
        The server-assigned ``product_version`` for the new release.

    Raises:
        ValueError: When the resolved current version is not a valid semver
            core.
    """
    current = latest_release_version if latest_release_version is not None else base_version
    return bump_minor(current)
