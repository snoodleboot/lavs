"""Response body for the dependency-graph impact what-if."""

from app.models.responses.impacted_component_model import ImpactedComponentModel
from app.models.responses.response_model import ResponseModel


class ImpactResponseModel(ResponseModel):
    """The components a hypothetical major change to one component would impact.

    ``component_id`` is the hypothetically-changed component; ``impacted`` lists
    each transitive dependent with the change level propagation projects onto it.
    """

    component_id: str
    impacted: list[ImpactedComponentModel]
