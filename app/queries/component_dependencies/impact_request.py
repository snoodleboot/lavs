"""Internal query input for the dependency-graph impact what-if."""

from app.models.requests.request_model import RequestModel


class ImpactRequest(RequestModel):
    """Identifies the product and the component to hypothetically change."""

    product_id: str
    component_id: str
