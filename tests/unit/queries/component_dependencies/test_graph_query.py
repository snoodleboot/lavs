"""Unit tests for :class:`GraphQuery`."""

from unittest import IsolatedAsyncioTestCase

from app.queries.component_dependencies.graph_query import GraphQuery
from app.queries.products.product_id_request import ProductIdRequest
from tests.unit.queries.component_dependencies.dependency_fixtures import (
    make_connection,
    seed_component,
    seed_edge,
    seed_product,
)


class TestGraphQuery(IsolatedAsyncioTestCase):
    """Behaviour of the product dependency-graph query."""

    async def test_returns_nodes_and_edges(self) -> None:
        """The graph lists the product's components and its edges."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        api = seed_component(conn, product_id, "api")
        core = seed_component(conn, product_id, "core")
        seed_edge(conn, product_id, api, core)
        data = ProductIdRequest(product_id=product_id)

        # Act
        graph = await GraphQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(graph.product_id, product_id)
        self.assertEqual({node.id for node in graph.nodes}, {api, core})
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges[0].from_component_id, api)
        self.assertEqual(graph.edges[0].to_component_id, core)

    async def test_empty_graph_has_no_nodes_or_edges(self) -> None:
        """A product with no components/edges yields empty lists."""
        # Arrange
        conn = make_connection()
        product_id = seed_product(conn)
        data = ProductIdRequest(product_id=product_id)

        # Act
        graph = await GraphQuery().execute(data=data, connection=conn)

        # Assert
        self.assertEqual(graph.nodes, [])
        self.assertEqual(graph.edges, [])
