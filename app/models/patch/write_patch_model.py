from pydantic import BaseModel


class WritePatchModel(BaseModel):
    application_name: str
