"""Response body describing a component dependency edge."""

from app.models.responses.response_model import ResponseModel


class DependencyResponseModel(ResponseModel):
    """A dependency edge: ``from_component_id`` depends on ``to_component_id``."""

    id: str
    product_id: str
    from_component_id: str
    to_component_id: str
    created_at: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "product_id": "01KW8WHA6STWW5N1VYRSHDTK1P",
                    "from_component_id": "01KW8WHA6STWW5N1VYRSHDTK1Q",
                    "to_component_id": "01KW8WHA6STWW5N1VYRSHDTK1R",
                    "created_at": "2026-08-22T12:00:00Z",
                }
            ]
        }
    }
