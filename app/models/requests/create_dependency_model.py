"""Request body for creating a component dependency edge."""

from app.models.requests.request_model import RequestModel
from app.models.types.ulid_id import UlidId


class CreateDependencyModel(RequestModel):
    """JSON body for ``POST /products/{id}/dependencies``.

    The owning product comes from the path; the body carries only the two
    component endpoints. ``from_component_id`` depends on ``to_component_id``.
    See ``docs/design/API_CONTRACT.md``.
    """

    from_component_id: UlidId
    to_component_id: UlidId

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "from_component_id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "to_component_id": "01KW8WHA6STWW5N1VYRSHDTK1P",
                }
            ]
        }
    }
