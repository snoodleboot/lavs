"""Shared assembly of a release's frozen component manifest.

Both read paths — the product ledger and the single-release fetch — need the
identical join across ``release_components`` → ``components`` (for the name) and
``versions`` (for the rendered version string). That logic lives here once so
the two queries stay thin and the manifest shape is built in exactly one place.
"""

from app.connections.db_session import DbSession
from app.models.responses.release_component_response_model import (
    ReleaseComponentResponseModel,
)

# The join is kept as a template: the ``IN`` list is expanded to a matching run
# of positional ``?`` placeholders whose count is derived solely from how many
# release ids were requested — never from their values. Every value is bound as
# a parameter, so the statement stays fully parameterized.
_MANIFEST_SELECT = (
    "SELECT rc.release_id, rc.component_id, c.name, rc.version_id, "
    "v.major, v.minor, v.patch, v.prerelease, rc.change_level "
    "FROM release_components rc "
    "JOIN components c ON rc.component_id = c.id "
    "JOIN versions v ON rc.version_id = v.id "
    "WHERE rc.release_id IN ({placeholders}) "
    "ORDER BY c.name, rc.component_id"
)


class ReleaseManifestReader:
    """Read the pinned component manifest for one or more releases.

    Returns the manifests grouped by ``release_id`` so a caller holding several
    release rows (the ledger) resolves every manifest in a single round trip,
    while the single-release caller passes a one-element list.
    """

    def read(
        self, conn: DbSession, release_ids: list[str]
    ) -> dict[str, list[ReleaseComponentResponseModel]]:
        """Fetch the frozen manifests for the given releases.

        Args:
            conn: The live DuckDB connection to read from.
            release_ids: The releases whose manifests to assemble.

        Returns:
            A mapping of ``release_id`` to its manifest entries, each ordered by
            component name then component id. Releases with no pinned components
            are simply absent from the mapping (the caller substitutes ``[]``).
        """
        if not release_ids:
            return {}

        placeholders = ", ".join("?" for _ in release_ids)
        statement = _MANIFEST_SELECT.format(placeholders=placeholders)
        rows = conn.execute(statement, release_ids).fetchall()

        grouped: dict[str, list[ReleaseComponentResponseModel]] = {}
        for row in rows:
            release_id = str(row[0])
            change_level = row[8]
            component = ReleaseComponentResponseModel(
                component_id=str(row[1]),
                name=str(row[2]),
                version_id=str(row[3]),
                version=self._version_string(row[4], row[5], row[6], row[7]),
                change_level=None if change_level is None else str(change_level),
            )
            grouped.setdefault(release_id, []).append(component)
        return grouped

    @staticmethod
    def _version_string(major: object, minor: object, patch: object, prerelease: object) -> str:
        """Render a pinned version as ``major.minor.patch[-prerelease]``.

        Args:
            major: The major component of the semantic version.
            minor: The minor component of the semantic version.
            patch: The patch component of the semantic version.
            prerelease: The optional prerelease label, or ``None``.

        Returns:
            The rendered version string, with the ``-prerelease`` suffix only
            when a prerelease label is present.
        """
        core = f"{major}.{minor}.{patch}"
        if prerelease is None:
            return core
        return f"{core}-{prerelease}"
