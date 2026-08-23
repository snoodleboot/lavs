"""Query that removes a dependency edge from a product's graph."""

from app.connections.db_session import DbSession
from app.errors.not_found_error import NotFoundError
from app.queries.component_dependencies.remove_dependency_request import (
    RemoveDependencyRequest,
)
from app.queries.query import Query

_SELECT_EDGE = (
    "SELECT id FROM component_dependencies "
    "WHERE product_id = ? AND from_component_id = ? AND to_component_id = ?"
)
_DELETE_EDGE = "DELETE FROM component_dependencies WHERE id = ?"


class RemoveDependencyQuery(Query[None]):
    """Delete one ``from -> to`` dependency edge, or 404 when it is absent."""

    async def apply(self, data: RemoveDependencyRequest, conn: DbSession) -> None:
        """Remove the identified edge.

        Args:
            data: The product id and the two component endpoints.
            conn: The live database connection.

        Raises:
            NotFoundError: When no such edge exists.
        """
        row = conn.execute(
            _SELECT_EDGE,
            [data.product_id, data.from_component_id, data.to_component_id],
        ).fetchone()
        if row is None:
            raise NotFoundError(
                message="This dependency edge does not exist.",
                details={
                    "product_id": data.product_id,
                    "from_component_id": data.from_component_id,
                    "to_component_id": data.to_component_id,
                },
            )
        conn.execute(_DELETE_EDGE, [str(row[0])])
