"""Internal query input for adding a dependency edge."""

from app.models.requests.request_model import RequestModel


class CreateDependencyRequest(RequestModel):
    """Carries the product and the two component endpoints of a new edge.

    The product id comes from the route path (not the HTTP body), so this
    internal input composes it with the validated body fields.
    """

    product_id: str
    from_component_id: str
    to_component_id: str
