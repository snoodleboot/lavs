"""Response body describing a product's dependency graph."""

from app.models.responses.component_response_model import ComponentResponseModel
from app.models.responses.dependency_response_model import DependencyResponseModel
from app.models.responses.response_model import ResponseModel


class GraphResponseModel(ResponseModel):
    """A product's components (nodes) and their dependency edges."""

    product_id: str
    nodes: list[ComponentResponseModel]
    edges: list[DependencyResponseModel]
