"""Query that fetches a single release with its frozen manifest."""

from app.connections.db_session import DbSession
from app.errors.not_found_error import NotFoundError
from app.models.responses.release_response_model import ReleaseResponseModel
from app.queries.query import Query
from app.queries.releases_read.release_id_request import ReleaseIdRequest
from app.queries.releases_read.release_manifest_reader import ReleaseManifestReader
from app.queries.releases_read.release_response_mapper import ReleaseResponseMapper

_RELEASE_SELECT = (
    "SELECT id, product_id, product_version, label, notes, created_at, "
    "bump_level, bump_rationale FROM releases WHERE id = ?"
)


class GetReleaseByIdQuery(Query[ReleaseResponseModel]):
    """Return one release with its frozen manifest, or raise 404 when absent.

    Reuses :class:`ReleaseManifestReader` so the pinned manifest is assembled by
    the same join the ledger uses. Strictly read-only.
    """

    async def apply(self, data: ReleaseIdRequest, conn: DbSession) -> ReleaseResponseModel:
        """Fetch the release identified by ``data.release_id``.

        Args:
            data: The request carrying the target release's ULID.
            conn: The live DuckDB connection to read from.

        Returns:
            The matching release with its frozen manifest.

        Raises:
            NotFoundError: When no release carries the requested id.
        """
        row = conn.execute(_RELEASE_SELECT, [data.release_id]).fetchone()
        if row is None:
            raise NotFoundError(
                message=f"No release exists with id '{data.release_id}'.",
                details={"release_id": data.release_id},
            )

        release_id = str(row[0])
        manifest = ReleaseManifestReader().read(conn, [release_id]).get(release_id, [])
        return ReleaseResponseMapper.to_model(row, manifest)
