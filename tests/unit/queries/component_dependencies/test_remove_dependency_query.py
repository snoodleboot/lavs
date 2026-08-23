"""Unit tests for :class:`RemoveDependencyQuery`."""

from unittest import IsolatedAsyncioTestCase

from app.errors.not_found_error import NotFoundError
from app.queries.component_dependencies.remove_dependency_query import (
    RemoveDependencyQuery,
)
from app.queries.component_dependencies.remove_dependency_request import (
    RemoveDependencyRequest,
)
from tests.unit.queries.component_dependencies.dependency_fixtures import (
    make_connection,
    seed_component,
    seed_edge,
    seed_product,
)


class TestRemoveDependencyQuery(IsolatedAsyncioTestCase):
    """Behaviour of removing a dependency edge."""

    async def test_removes_existing_edge(self) -> None:
        """An existing edge is deleted and no longer present."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        from_id = seed_component(conn, product_id, "api")
        to_id = seed_component(conn, product_id, "core")
        seed_edge(conn, product_id, from_id, to_id)
        data = RemoveDependencyRequest(
            product_id=product_id, from_component_id=from_id, to_component_id=to_id
        )

        # Act
        await RemoveDependencyQuery().execute(data=data, connection=conn)

        # Assert
        remaining = conn.execute("SELECT COUNT(*) FROM component_dependencies").fetchone()
        assert remaining is not None
        self.assertEqual(remaining[0], 0)

    async def test_missing_edge_raises_not_found(self) -> None:
        """Removing an absent edge surfaces as 404."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        from_id = seed_component(conn, product_id, "api")
        to_id = seed_component(conn, product_id, "core")
        data = RemoveDependencyRequest(
            product_id=product_id, from_component_id=from_id, to_component_id=to_id
        )

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await RemoveDependencyQuery().execute(data=data, connection=conn)
