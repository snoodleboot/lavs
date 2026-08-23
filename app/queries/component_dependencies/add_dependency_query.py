"""Query that adds a dependency edge between two components of a product."""

from app.connections.db_session import DbSession
from app.domain.dependency_graph import would_create_cycle
from app.errors.conflict_error import ConflictError
from app.errors.not_found_error import NotFoundError
from app.models.responses.dependency_response_model import DependencyResponseModel
from app.models.types.ulid_id import new_ulid
from app.queries.component_dependencies.create_dependency_request import (
    CreateDependencyRequest,
)
from app.queries.component_dependencies.dependency_response_mapper import (
    DependencyResponseMapper,
)
from app.queries.query import Query

_SELECT_PRODUCT = "SELECT id FROM products WHERE id = ?"
_SELECT_COMPONENT = "SELECT id, product_id FROM components WHERE id = ?"
_SELECT_EDGES = (
    "SELECT from_component_id, to_component_id FROM component_dependencies WHERE product_id = ?"
)
_SELECT_EDGE = (
    "SELECT id FROM component_dependencies "
    "WHERE product_id = ? AND from_component_id = ? AND to_component_id = ?"
)
_INSERT_EDGE = (
    "INSERT INTO component_dependencies "
    "(id, product_id, from_component_id, to_component_id) VALUES (?, ?, ?, ?)"
)
_SELECT_CREATED = (
    "SELECT id, product_id, from_component_id, to_component_id, created_at "
    "FROM component_dependencies WHERE id = ?"
)


class AddDependencyQuery(Query[DependencyResponseModel]):
    """Add one ``from -> to`` dependency edge to a product's graph.

    The invariants are enforced in the application layer so the identical guard
    holds on every backend: the product and both components must exist and both
    components must belong to the product; the edge must not be a self-edge, a
    duplicate, or one that would close a cycle. Each failure surfaces as a typed
    :class:`NotFoundError` (404) or :class:`ConflictError` (409) rather than a raw
    constraint violation.
    """

    async def apply(
        self, data: CreateDependencyRequest, conn: DbSession
    ) -> DependencyResponseModel:
        """Validate and insert the edge, returning its response model.

        Args:
            data: The product id and the two component endpoints.
            conn: The live database connection.

        Returns:
            The persisted edge as a :class:`DependencyResponseModel`.

        Raises:
            NotFoundError: When the product or either component does not exist.
            ConflictError: On a self-edge, a cross-product endpoint, a duplicate
                edge, or an edge that would introduce a cycle.
        """
        if conn.execute(_SELECT_PRODUCT, [data.product_id]).fetchone() is None:
            raise NotFoundError(
                message=f"Product '{data.product_id}' does not exist.",
                details={"product_id": data.product_id},
            )

        self._assert_component(conn, data.product_id, data.from_component_id)
        self._assert_component(conn, data.product_id, data.to_component_id)

        if data.from_component_id == data.to_component_id:
            raise ConflictError(
                message="A component cannot depend on itself.",
                details={"component_id": data.from_component_id},
            )

        duplicate = conn.execute(
            _SELECT_EDGE,
            [data.product_id, data.from_component_id, data.to_component_id],
        ).fetchone()
        if duplicate is not None:
            raise ConflictError(
                message="This dependency edge already exists.",
                details={
                    "from_component_id": data.from_component_id,
                    "to_component_id": data.to_component_id,
                },
            )

        edges = [
            (str(row[0]), str(row[1]))
            for row in conn.execute(_SELECT_EDGES, [data.product_id]).fetchall()
        ]
        if would_create_cycle(edges, data.from_component_id, data.to_component_id):
            raise ConflictError(
                message="This dependency edge would introduce a cycle.",
                details={
                    "from_component_id": data.from_component_id,
                    "to_component_id": data.to_component_id,
                },
            )

        edge_id = new_ulid()
        conn.execute(
            _INSERT_EDGE,
            [edge_id, data.product_id, data.from_component_id, data.to_component_id],
        )
        row = conn.execute(_SELECT_CREATED, [edge_id]).fetchone()
        assert row is not None, "The dependency edge just inserted was not found."
        return DependencyResponseMapper.to_model(row)

    def _assert_component(self, conn: DbSession, product_id: str, component_id: str) -> None:
        """Assert ``component_id`` exists and belongs to ``product_id``.

        Args:
            conn: The live database connection.
            product_id: The owning product's id.
            component_id: The component to check.

        Raises:
            NotFoundError: When the component does not exist.
            ConflictError: When the component belongs to a different product.
        """
        row = conn.execute(_SELECT_COMPONENT, [component_id]).fetchone()
        if row is None:
            raise NotFoundError(
                message=f"Component '{component_id}' does not exist.",
                details={"component_id": component_id},
            )
        if str(row[1]) != product_id:
            raise ConflictError(
                message=f"Component '{component_id}' does not belong to product '{product_id}'.",
                details={"component_id": component_id, "product_id": product_id},
            )
