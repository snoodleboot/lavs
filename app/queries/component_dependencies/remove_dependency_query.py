"""Query that removes a dependency edge from a product's graph."""

from app.connections.db_session import DbSession
from app.errors.not_found_error import NotFoundError
from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.events.event_type import EventType
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
    """Delete one ``from -> to`` dependency edge, or 404 when it is absent.

    When an :class:`EventBus` is supplied, a ``dependency.removed`` domain event
    is published for the product after the edge is deleted.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Create the query, optionally wired to an event bus.

        Args:
            event_bus: The event bus to publish ``dependency.removed`` on, or
                ``None`` to run without emitting events.
        """
        super().__init__()
        self._event_bus = event_bus

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
        edge_id = str(row[0])
        conn.execute(_DELETE_EDGE, [edge_id])

        if self._event_bus is not None:
            await self._event_bus.publish(
                DomainEvent(
                    event_type=EventType.DEPENDENCY_REMOVED,
                    product_id=data.product_id,
                    data={
                        "dependency": {
                            "id": edge_id,
                            "product_id": data.product_id,
                            "from_component_id": data.from_component_id,
                            "to_component_id": data.to_component_id,
                        }
                    },
                )
            )
