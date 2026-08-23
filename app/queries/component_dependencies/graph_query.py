"""Query that returns a product's dependency graph (nodes + edges)."""

from app.connections.db_session import DbSession
from app.models.enums.component_kind import ComponentKind
from app.models.responses.component_response_model import ComponentResponseModel
from app.models.responses.graph_response_model import GraphResponseModel
from app.queries.component_dependencies.dependency_response_mapper import (
    DependencyResponseMapper,
)
from app.queries.products.product_id_request import ProductIdRequest
from app.queries.query import Query

_SELECT_COMPONENTS = (
    "SELECT id, product_id, name, kind FROM components WHERE product_id = ? ORDER BY name, id"
)
_SELECT_EDGES = (
    "SELECT id, product_id, from_component_id, to_component_id, created_at "
    "FROM component_dependencies WHERE product_id = ? ORDER BY created_at, id"
)


class GraphQuery(Query[GraphResponseModel]):
    """Return the components and dependency edges of one product.

    The caller is expected to have confirmed the product exists (so an unknown
    product yields 404, not an empty graph); this query returns the — possibly
    empty — nodes and edges for that product.
    """

    async def apply(self, data: ProductIdRequest, conn: DbSession) -> GraphResponseModel:
        """Select the product's components and edges.

        Args:
            data: The request carrying the product's id.
            conn: The live database connection.

        Returns:
            The product's dependency graph.
        """
        nodes = [
            ComponentResponseModel(
                id=str(row[0]),
                product_id=str(row[1]),
                name=str(row[2]),
                kind=ComponentKind(str(row[3])),
            )
            for row in conn.execute(_SELECT_COMPONENTS, [data.product_id]).fetchall()
        ]
        edges = [
            DependencyResponseMapper.to_model(row)
            for row in conn.execute(_SELECT_EDGES, [data.product_id]).fetchall()
        ]
        return GraphResponseModel(product_id=data.product_id, nodes=nodes, edges=edges)
