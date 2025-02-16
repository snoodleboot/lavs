from pydantic import BaseModel


class WriteModel(BaseModel):
    """Model for writing a new version record."""
    application_name: str
    major: int
    minor: int
    patch: int
