"""Map DuckDB result rows onto a release's frozen response manifest.

The cut query loads a release's row and its pinned component rows with fixed
column projections; the row-to-model translation lives here so both the
fresh-cut and idempotent-replay paths build the response identically.
"""

from datetime import datetime
from typing import Any

from app.models.responses.release_component_response_model import (
    ReleaseComponentResponseModel,
)
from app.models.responses.release_response_model import ReleaseResponseModel

_PRERELEASE_SEPARATOR = "-"


def format_version(major: int, minor: int, patch: int, prerelease: str | None) -> str:
    """Render semver parts as ``major.minor.patch`` with an optional suffix.

    Args:
        major: Semver major.
        minor: Semver minor.
        patch: Semver patch.
        prerelease: Optional prerelease label, or ``None``.

    Returns:
        ``"major.minor.patch"``, extended with ``-prerelease`` when present.
    """
    core = f"{major}.{minor}.{patch}"
    if prerelease:
        return f"{core}{_PRERELEASE_SEPARATOR}{prerelease}"
    return core


def to_release_components(
    description: list[Any], rows: list[tuple[Any, ...]]
) -> list[ReleaseComponentResponseModel]:
    """Build the frozen component manifest from the pinned-version rows.

    Args:
        description: The column description of the executed relation.
        rows: The manifest rows (one per pinned component).

    Returns:
        One :class:`ReleaseComponentResponseModel` per row.
    """
    columns = [entry[0] for entry in description]
    components: list[ReleaseComponentResponseModel] = []
    for row in rows:
        fields = dict(zip(columns, row, strict=False))
        change_level = fields.get("change_level")
        components.append(
            ReleaseComponentResponseModel(
                component_id=fields["component_id"],
                name=fields["name"],
                version_id=fields["version_id"],
                version=format_version(
                    fields["major"], fields["minor"], fields["patch"], fields["prerelease"]
                ),
                change_level=None if change_level is None else str(change_level),
            )
        )
    return components


def to_release_response(
    description: list[Any],
    row: tuple[Any, ...],
    components: list[ReleaseComponentResponseModel],
) -> ReleaseResponseModel:
    """Build a :class:`ReleaseResponseModel` from a release row and its manifest.

    The ``created_at`` column arrives as a ``datetime`` from DuckDB's
    ``TIMESTAMP`` type; it is rendered in ISO-8601 text form for the response.

    Args:
        description: The column description of the release relation.
        row: The single release row.
        components: The frozen component manifest for the release.

    Returns:
        The populated release response model.
    """
    columns = [entry[0] for entry in description]
    fields = dict(zip(columns, row, strict=False))
    created_at = fields["created_at"]
    created_at_text = (
        created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    )
    bump_level = fields.get("bump_level")
    bump_rationale = fields.get("bump_rationale")
    return ReleaseResponseModel(
        id=fields["id"],
        product_id=fields["product_id"],
        product_version=fields["product_version"],
        label=fields["label"],
        notes=fields["notes"],
        created_at=created_at_text,
        bump_level=None if bump_level is None else str(bump_level),
        bump_rationale=None if bump_rationale is None else str(bump_rationale),
        components=components,
    )
