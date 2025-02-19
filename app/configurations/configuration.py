from typing import Optional

from pydantic import BaseModel


class Configuration(BaseModel):
    version: int = 0
    application_name: Optional[str] = "lavs-api"
