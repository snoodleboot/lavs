"""Unit tests for :class:`AddDependencyQuery`."""

from unittest import IsolatedAsyncioTestCase

from app.errors.conflict_error import ConflictError
from app.errors.not_found_error import NotFoundError
from app.events.event_bus import EventBus
from app.events.event_type import EventType
from app.models.types.ulid_id import new_ulid
from app.queries.component_dependencies.add_dependency_query import AddDependencyQuery
from app.queries.component_dependencies.create_dependency_request import (
    CreateDependencyRequest,
)
from tests.unit.queries.component_dependencies.dependency_fixtures import (
    make_connection,
    seed_component,
    seed_edge,
    seed_product,
)


class TestAddDependencyQuery(IsolatedAsyncioTestCase):
    """Behaviour of adding a dependency edge."""

    async def test_adds_edge_and_returns_model(self) -> None:
        """A valid edge is persisted and returned with its ids and timestamp."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        from_id = seed_component(conn, product_id, "api")
        to_id = seed_component(conn, product_id, "core")
        data = CreateDependencyRequest(
            product_id=product_id, from_component_id=from_id, to_component_id=to_id
        )

        # Act
        result = await AddDependencyQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(result.product_id, product_id)
        self.assertEqual(result.from_component_id, from_id)
        self.assertEqual(result.to_component_id, to_id)
        self.assertTrue(result.id)
        self.assertTrue(result.created_at)

    async def test_unknown_product_raises_not_found(self) -> None:
        """A missing product surfaces as 404."""
        # Arrange
        conn = make_connection()
        data = CreateDependencyRequest(
            product_id=new_ulid(), from_component_id=new_ulid(), to_component_id=new_ulid()
        )

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await AddDependencyQuery().execute(data=data, connection=conn)

    async def test_unknown_component_raises_not_found(self) -> None:
        """A missing component endpoint surfaces as 404."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        from_id = seed_component(conn, product_id, "api")
        data = CreateDependencyRequest(
            product_id=product_id, from_component_id=from_id, to_component_id=new_ulid()
        )

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await AddDependencyQuery().execute(data=data, connection=conn)

    async def test_self_edge_raises_conflict(self) -> None:
        """A component depending on itself is rejected as 409."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        component_id = seed_component(conn, product_id, "api")
        data = CreateDependencyRequest(
            product_id=product_id,
            from_component_id=component_id,
            to_component_id=component_id,
        )

        # Act / Assert
        with self.assertRaises(ConflictError):
            await AddDependencyQuery().execute(data=data, connection=conn)

    async def test_cross_product_component_raises_conflict(self) -> None:
        """An endpoint belonging to another product is rejected as 409."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        other_product = seed_product(conn)
        from_id = seed_component(conn, product_id, "api")
        foreign_id = seed_component(conn, other_product, "core")
        data = CreateDependencyRequest(
            product_id=product_id, from_component_id=from_id, to_component_id=foreign_id
        )

        # Act / Assert
        with self.assertRaises(ConflictError):
            await AddDependencyQuery().execute(data=data, connection=conn)

    async def test_duplicate_edge_raises_conflict(self) -> None:
        """Re-adding an existing edge is rejected as 409."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        from_id = seed_component(conn, product_id, "api")
        to_id = seed_component(conn, product_id, "core")
        seed_edge(conn, product_id, from_id, to_id)
        data = CreateDependencyRequest(
            product_id=product_id, from_component_id=from_id, to_component_id=to_id
        )

        # Act / Assert
        with self.assertRaises(ConflictError):
            await AddDependencyQuery().execute(data=data, connection=conn)

    async def test_publishes_dependency_added_event(self) -> None:
        """A successful add publishes a dependency.added event for the product."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        from_id = seed_component(conn, product_id, "api")
        to_id = seed_component(conn, product_id, "core")
        bus = EventBus()
        queue = bus.subscribe(product_id)
        data = CreateDependencyRequest(
            product_id=product_id, from_component_id=from_id, to_component_id=to_id
        )

        # Act
        await AddDependencyQuery(bus).execute(data=data, connection=conn)

        # Assert
        event = queue.get_nowait()
        self.assertEqual(event.event_type, EventType.DEPENDENCY_ADDED)
        self.assertEqual(event.product_id, product_id)
        self.assertEqual(event.data["dependency"]["from_component_id"], from_id)

    async def test_cycle_raises_conflict(self) -> None:
        """An edge that would close a cycle is rejected as 409."""
        # Arrange: a -> b, b -> c already exist; adding c -> a closes the cycle.
        conn = make_connection()
        product_id = seed_product(conn)
        a = seed_component(conn, product_id, "a")
        b = seed_component(conn, product_id, "b")
        c = seed_component(conn, product_id, "c")
        seed_edge(conn, product_id, a, b)
        seed_edge(conn, product_id, b, c)
        data = CreateDependencyRequest(
            product_id=product_id, from_component_id=c, to_component_id=a
        )

        # Act / Assert
        with self.assertRaises(ConflictError):
            await AddDependencyQuery().execute(data=data, connection=conn)
