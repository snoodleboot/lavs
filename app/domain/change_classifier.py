"""Pure classification of a single component's change since the last release.

A component's *own* change level is derived by comparing its currently-active
version to the version pinned for it in the previous release manifest. The
comparison is by the highest position that differs, **regardless of direction**
— a rollback (``2.0.0 -> 1.0.0``) is a deliberate material change and classifies
by its major position (see ``docs/planning/P9_MULTIAGENT_EXECUTION_PLAN.md`` §7a,
gaps G-P9b/G-P9c/G-P9g). These helpers are pure so the derivation can be
unit-tested without a database.
"""

from app.models.enums.bump_level import BumpLevel

#: A version's numeric core plus optional prerelease: ``(major, minor, patch, prerelease)``.
VersionTuple = tuple[int, int, int, str | None]


def classify_change(prior: VersionTuple | None, current: VersionTuple) -> BumpLevel:
    """Classify a component's own change from ``prior`` to ``current``.

    Args:
        prior: The component's version pinned in the previous release manifest,
            or ``None`` when the component was not in it (newly added).
        current: The component's currently-active version.

    Returns:
        The own-change level: ``MINOR`` for a newly-added component (G-P9b);
        otherwise the level of the highest position that differs, with a
        prerelease-only difference counting as ``PATCH`` (G-P9c); ``NONE`` when
        the two versions are identical.
    """
    if prior is None:
        return BumpLevel.MINOR

    prior_major, prior_minor, prior_patch, prior_prerelease = prior
    current_major, current_minor, current_patch, current_prerelease = current

    if prior_major != current_major:
        return BumpLevel.MAJOR
    if prior_minor != current_minor:
        return BumpLevel.MINOR
    if prior_patch != current_patch:
        return BumpLevel.PATCH
    if (prior_prerelease or None) != (current_prerelease or None):
        return BumpLevel.PATCH
    return BumpLevel.NONE
