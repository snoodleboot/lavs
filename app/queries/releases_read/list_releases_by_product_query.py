"""Query that lists a product's release ledger, newest first."""

from app.connections.db_session import DbSession
from app.errors.not_found_error import NotFoundError
from app.models.responses.release_response_model import ReleaseResponseModel
from app.queries.products.product_id_request import ProductIdRequest
from app.queries.query import Query
from app.queries.releases_read.release_manifest_reader import ReleaseManifestReader
from app.queries.releases_read.release_response_mapper import ReleaseResponseMapper

# Static projections kept as constants so the SELECTs carry no interpolation.
_PRODUCT_EXISTS = "SELECT 1 FROM products WHERE id = ?"
# Newest first: ``created_at`` descending, with ``id`` descending as the
# deterministic tie-break for releases sharing a timestamp.
_RELEASES_SELECT = (
    "SELECT id, product_id, product_version, label, notes, created_at, "
    "bump_level, bump_rationale "
    "FROM releases WHERE product_id = ? "
    "ORDER BY created_at DESC, id DESC"
)


class ListReleasesByProductQuery(Query[list[ReleaseResponseModel]]):
    """Return a product's releases, newest first, each with its frozen manifest.

    The parent product's existence is asserted first so an unknown product
    yields :class:`NotFoundError` (HTTP 404) rather than a misleading empty
    list; a known product with no releases returns ``[]``. Strictly read-only.
    """

    async def apply(self, data: ProductIdRequest, conn: DbSession) -> list[ReleaseResponseModel]:
        """Read the product's release ledger and attach each frozen manifest.

        Args:
            data: The request carrying the parent product's ULID.
            conn: The live DuckDB connection to read from.

        Returns:
            The product's releases newest-first; empty when it has none.

        Raises:
            NotFoundError: When no product carries ``data.product_id``.
        """
        if conn.execute(_PRODUCT_EXISTS, [data.product_id]).fetchone() is None:
            raise NotFoundError(
                message=f"No product exists with id '{data.product_id}'.",
                details={"product_id": data.product_id},
            )

        rows = conn.execute(_RELEASES_SELECT, [data.product_id]).fetchall()
        release_ids = [str(row[0]) for row in rows]
        manifests = ReleaseManifestReader().read(conn, release_ids)
        return [ReleaseResponseMapper.to_model(row, manifests.get(str(row[0]), [])) for row in rows]
