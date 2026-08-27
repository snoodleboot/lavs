"""Query that inserts a new product and returns its response model."""

from app.connections.db_session import DbSession
from app.errors.conflict_error import ConflictError
from app.models.enums.bump_policy import BumpPolicy
from app.models.requests.create_product_model import CreateProductModel
from app.models.responses.product_response_model import ProductResponseModel
from app.models.types.ulid_id import new_ulid
from app.queries.products.product_response_mapper import ProductResponseMapper
from app.queries.query import Query


class CreateProductQuery(Query[ProductResponseModel]):
    """Persist a new product, enforcing a unique ``name``.

    A fresh ULID is minted for the row. If another product already carries the
    requested ``name`` a :class:`ConflictError` is raised so the route returns
    HTTP 409 through the registered envelope handler.
    """

    async def apply(self, data: CreateProductModel, conn: DbSession) -> ProductResponseModel:
        """Insert the product and return the stored row as a response model.

        Args:
            data: The validated create-product request body.
            conn: The live DuckDB connection to run against.

        Returns:
            The created product, including its server-assigned ``created_at``.

        Raises:
            ConflictError: When a product with the same ``name`` already exists.
        """
        existing = conn.execute("SELECT id FROM products WHERE name = ?", [data.name]).fetchone()
        if existing is not None:
            raise ConflictError(
                message=f"A product named '{data.name}' already exists.",
                details={"name": data.name},
            )

        product_id = new_ulid()
        conn.execute(
            "INSERT INTO products (id, name, description, bump_policy) VALUES (?, ?, ?, ?)",
            [product_id, data.name, data.description, BumpPolicy.DEFAULT.value],
        )

        row = conn.execute(
            "SELECT id, name, description, base_version, created_at FROM products WHERE id = ?",
            [product_id],
        ).fetchone()
        if row is None:
            raise ConflictError(
                message="The product could not be read back after insertion.",
                details={"id": product_id},
            )
        return ProductResponseMapper.to_model(row)
