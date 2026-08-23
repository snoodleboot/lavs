"""Unit tests for :class:`ImpactQuery`."""

from unittest import IsolatedAsyncioTestCase

from app.errors.not_found_error import NotFoundError
from app.models.types.ulid_id import new_ulid
from app.queries.component_dependencies.impact_query import ImpactQuery
from app.queries.component_dependencies.impact_request import ImpactRequest
from tests.unit.queries.component_dependencies.dependency_fixtures import (
    make_connection,
    seed_component,
    seed_edge,
    seed_product,
)


class TestImpactQuery(IsolatedAsyncioTestCase):
    """Behaviour of the dependency-graph impact what-if."""

    async def test_lists_transitive_dependents_with_projected_levels(self) -> None:
        """A hypothetical major change projects onto each transitive dependent."""
        # Arrange: a -> b -> c (a depends on b, b depends on c).
        conn = make_connection()
        product_id = seed_product(conn)
        a = seed_component(conn, product_id, "a")
        b = seed_component(conn, product_id, "b")
        c = seed_component(conn, product_id, "c")
        seed_edge(conn, product_id, a, b)
        seed_edge(conn, product_id, b, c)
        data = ImpactRequest(product_id=product_id, component_id=c)

        # Act
        result = await ImpactQuery().execute(data=data, connection=conn)

        # Assert: b feels P(MAJOR)=minor, a feels P(minor)=patch.
        projected = {entry.component_id: entry.projected_change_level for entry in result.impacted}
        self.assertEqual(result.component_id, c)
        self.assertEqual(projected, {b: "minor", a: "patch"})

    async def test_component_with_no_dependents_returns_empty(self) -> None:
        """A component nothing depends on impacts nobody."""
        # Arrange: a -> b (a depends on b); nothing depends on a.
        conn = make_connection()
        product_id = seed_product(conn)
        a = seed_component(conn, product_id, "a")
        b = seed_component(conn, product_id, "b")
        seed_edge(conn, product_id, a, b)
        data = ImpactRequest(product_id=product_id, component_id=a)

        # Act
        result = await ImpactQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(result.impacted, [])

    async def test_unknown_product_raises_not_found(self) -> None:
        """An unknown product surfaces as 404."""
        # Arrange
        conn = make_connection()
        data = ImpactRequest(product_id=new_ulid(), component_id=new_ulid())

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await ImpactQuery().execute(data=data, connection=conn)

    async def test_unknown_component_raises_not_found(self) -> None:
        """A component not in the product surfaces as 404."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        data = ImpactRequest(product_id=product_id, component_id=new_ulid())

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await ImpactQuery().execute(data=data, connection=conn)
