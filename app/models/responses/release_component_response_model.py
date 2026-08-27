"""Response body describing one frozen component in a release manifest."""

from app.models.responses.response_model import ResponseModel


class ReleaseComponentResponseModel(ResponseModel):
    """A single entry of a release's frozen manifest.

    See ``docs/design/API_CONTRACT.md`` §3 (``Release.components[]``). Each entry
    pins the exact ``version_id`` that was ``active`` for the component at cut
    time; ``version`` is that version rendered as ``major.minor.patch`` with an
    optional ``-prerelease`` suffix.
    """

    component_id: str
    name: str
    version_id: str
    version: str
    change_level: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "component_id": "01KW8WHA6STWW5N1VYRSHDTK1P",
                    "name": "lavs-api",
                    "version_id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "version": "2.4.0",
                }
            ]
        }
    }
