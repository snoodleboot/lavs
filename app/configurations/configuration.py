from typing import Optional

from pydantic import BaseModel


class Configuration(BaseModel):
    """Stores basic application configuration."""
    version: int = 0
    application_name: Optional[str] = "lavs-api"
    database_name: str = "test.db"
