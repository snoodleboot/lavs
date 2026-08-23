"""Routes for the ``/products`` resource.

Implements product listing, creation (with duplicate-name conflict handling),
single-product retrieval, and listing a product's components. The prefix, tag,
and mandatory authenticated-principal dependency are fixed on the shared ``router`` below; each
handler delegates persistence to a dedicated :class:`~app.queries.query.Query`
and reuses the application-managed DuckDB connection.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi import Query as QueryParam

from app.auth.require_principal import require_principal
from app.connections.db_dependency import get_db_connection
from app.connections.db_session import DbSession
from app.models.requests.create_dependency_model import CreateDependencyModel
from app.models.requests.create_product_model import CreateProductModel
from app.models.requests.request_model import RequestModel
from app.models.responses.component_response_model import ComponentResponseModel
from app.models.responses.dependency_response_model import DependencyResponseModel
from app.models.responses.graph_response_model import GraphResponseModel
from app.models.responses.impact_response_model import ImpactResponseModel
from app.models.responses.product_response_model import ProductResponseModel
from app.queries.component_dependencies.add_dependency_query import AddDependencyQuery
from app.queries.component_dependencies.create_dependency_request import (
    CreateDependencyRequest,
)
from app.queries.component_dependencies.graph_query import GraphQuery
from app.queries.component_dependencies.impact_query import ImpactQuery
from app.queries.component_dependencies.impact_request import ImpactRequest
from app.queries.component_dependencies.remove_dependency_query import (
    RemoveDependencyQuery,
)
from app.queries.component_dependencies.remove_dependency_request import (
    RemoveDependencyRequest,
)
from app.queries.products.create_product_query import CreateProductQuery
from app.queries.products.get_product_by_id_query import GetProductByIdQuery
from app.queries.products.list_components_by_product_query import (
    ListComponentsByProductQuery,
)
from app.queries.products.list_products_query import ListProductsQuery
from app.queries.products.product_id_request import ProductIdRequest

router = APIRouter(
    tags=["products"],
    prefix="/products",
    dependencies=[Depends(require_principal)],
)

DbConnection = Annotated[DbSession, Depends(get_db_connection)]


@router.get("", response_model=list[ProductResponseModel])
async def list_products(
    conn: DbConnection,
) -> list[ProductResponseModel]:
    """List every registered product.

    Args:
        conn: The application-managed DuckDB connection.

    Returns:
        All products; an empty list when none are registered.
    """
    return await ListProductsQuery().execute(data=RequestModel(), connection=conn)


@router.post(
    "",
    response_model=ProductResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    body: CreateProductModel,
    conn: DbConnection,
) -> ProductResponseModel:
    """Register a new product.

    Args:
        body: The create-product request body (``name`` required).
        conn: The application-managed DuckDB connection.

    Returns:
        The newly created product with its server-assigned id and timestamp.

    Raises:
        ConflictError: When a product with the same ``name`` already exists.
    """
    return await CreateProductQuery().execute(data=body, connection=conn)


@router.get("/{product_id}", response_model=ProductResponseModel)
async def get_product(
    product_id: str,
    conn: DbConnection,
) -> ProductResponseModel:
    """Retrieve a single product by its ULID identifier.

    Args:
        product_id: The target product's ULID string.
        conn: The application-managed DuckDB connection.

    Returns:
        The matching product.

    Raises:
        NotFoundError: When no product carries the given id.
    """
    return await GetProductByIdQuery().execute(
        data=ProductIdRequest(product_id=product_id), connection=conn
    )


@router.get(
    "/{product_id}/components",
    response_model=list[ComponentResponseModel],
)
async def list_product_components(
    product_id: str,
    conn: DbConnection,
) -> list[ComponentResponseModel]:
    """List the components belonging to a product.

    The product's existence is asserted first so an unknown product yields 404
    rather than a misleading empty list.

    Args:
        product_id: The parent product's ULID string.
        conn: The application-managed DuckDB connection.

    Returns:
        The product's components; an empty list when it has none.

    Raises:
        NotFoundError: When no product carries the given id.
    """
    request = ProductIdRequest(product_id=product_id)
    await GetProductByIdQuery().execute(data=request, connection=conn)
    return await ListComponentsByProductQuery().execute(data=request, connection=conn)


@router.get(
    "/{product_id}/graph",
    response_model=GraphResponseModel,
)
async def get_product_graph(
    product_id: str,
    conn: DbConnection,
) -> GraphResponseModel:
    """Return a product's dependency graph: its components and their edges.

    Args:
        product_id: The parent product's ULID string.
        conn: The application-managed DuckDB connection.

    Returns:
        The product's nodes and dependency edges.

    Raises:
        NotFoundError: When no product carries the given id.
    """
    request = ProductIdRequest(product_id=product_id)
    await GetProductByIdQuery().execute(data=request, connection=conn)
    return await GraphQuery().execute(data=request, connection=conn)


@router.get(
    "/{product_id}/impact",
    response_model=ImpactResponseModel,
)
async def get_product_impact(
    product_id: str,
    conn: DbConnection,
    component: Annotated[str, QueryParam(alias="component")],
) -> ImpactResponseModel:
    """Project a hypothetical major change to ``component`` across its dependents.

    Args:
        product_id: The parent product's ULID string.
        conn: The application-managed DuckDB connection.
        component: The component to hypothetically change (``component`` query
            parameter).

    Returns:
        The impacted dependents with their projected change levels.

    Raises:
        NotFoundError: When the product or component does not exist.
    """
    request = ImpactRequest(product_id=product_id, component_id=component)
    return await ImpactQuery().execute(data=request, connection=conn)


@router.post(
    "/{product_id}/dependencies",
    response_model=DependencyResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def add_product_dependency(
    product_id: str,
    body: CreateDependencyModel,
    conn: DbConnection,
) -> DependencyResponseModel:
    """Add a dependency edge (``from`` depends on ``to``) to a product's graph.

    Args:
        product_id: The parent product's ULID string.
        body: The two component endpoints.
        conn: The application-managed DuckDB connection.

    Returns:
        The persisted dependency edge.

    Raises:
        NotFoundError: When the product or either component does not exist.
        ConflictError: On a self-edge, cross-product endpoint, duplicate edge, or
            an edge that would introduce a cycle.
    """
    request = CreateDependencyRequest(
        product_id=product_id,
        from_component_id=body.from_component_id,
        to_component_id=body.to_component_id,
    )
    return await AddDependencyQuery().execute(data=request, connection=conn)


@router.delete(
    "/{product_id}/dependencies",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_product_dependency(
    product_id: str,
    conn: DbConnection,
    from_component_id: Annotated[str, QueryParam(alias="from")],
    to_component_id: Annotated[str, QueryParam(alias="to")],
) -> None:
    """Remove a dependency edge identified by its ``from`` and ``to`` endpoints.

    Args:
        product_id: The parent product's ULID string.
        conn: The application-managed DuckDB connection.
        from_component_id: The edge tail (``from`` query parameter).
        to_component_id: The edge head (``to`` query parameter).

    Raises:
        NotFoundError: When no such edge exists.
    """
    request = RemoveDependencyRequest(
        product_id=product_id,
        from_component_id=from_component_id,
        to_component_id=to_component_id,
    )
    await RemoveDependencyQuery().execute(data=request, connection=conn)
