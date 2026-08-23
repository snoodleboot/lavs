"""Internal query input for removing a dependency edge."""

from app.models.requests.request_model import RequestModel


class RemoveDependencyRequest(RequestModel):
    """Identifies a dependency edge by product and its two component endpoints."""

    product_id: str
    from_component_id: str
    to_component_id: str
