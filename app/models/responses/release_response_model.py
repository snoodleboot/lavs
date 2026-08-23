"""Response body describing an immutable, frozen release."""

from app.models.responses.release_component_response_model import (
    ReleaseComponentResponseModel,
)
from app.models.responses.response_model import ResponseModel


class ReleaseResponseModel(ResponseModel):
    """The ``Release`` schema from ``docs/design/API_CONTRACT.md`` §3 & §5.

    A release is a permanent, reproducible statement of the product composition:
    ``product_version`` is server-assigned and ``components`` pins the exact
    ``version_id`` of each component at cut time, so a cut release never changes.
    """

    id: str
    product_id: str
    product_version: str
    label: str | None
    notes: str | None
    created_at: str
    bump_level: str | None = None
    bump_rationale: str | None = None
    components: list[ReleaseComponentResponseModel]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "product_id": "01KW8WHA6STWW5N1VYRSHDTK1P",
                    "product_version": "5.1.0",
                    "label": "Aurora 5.1",
                    "notes": None,
                    "created_at": "2026-06-29T12:00:00Z",
                    "components": [
                        {
                            "component_id": "01KW8WHA6STWW5N1VYRSHDTK1Q",
                            "name": "lavs-api",
                            "version_id": "01KW8WHA6STWW5N1VYRSHDTK1R",
                            "version": "2.4.0",
                        }
                    ],
                }
            ]
        }
    }
