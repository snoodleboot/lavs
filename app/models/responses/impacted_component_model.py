"""Response entry describing one component impacted by a hypothetical change."""

from app.models.responses.response_model import ResponseModel


class ImpactedComponentModel(ResponseModel):
    """A dependent component and the change level a hypothetical bump projects onto it."""

    component_id: str
    projected_change_level: str
