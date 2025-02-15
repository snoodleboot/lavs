from pydantic import BaseModel


class WriteModel(BaseModel):
    application_name: str
    major: int
    minor: int
    patch: int
