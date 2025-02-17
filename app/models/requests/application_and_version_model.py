import re
from typing import Optional

import pydantic
from pydantic import field_validator, computed_field

from app.models.requests.request_model import RequestModel


class ApplicationAndVersionNameModel(RequestModel):
    application_name: str
    version: Optional[str] = None

    @field_validator('version', mode='before')
    @classmethod
    def validate_version(cls, field_value: str) -> str:
        rex = re.compile("[0-9]+\.[0-9]+\.[0-9]+")
        if rex.match(field_value):
            return field_value
        else:
            raise ValueError('version must be a semantic version number.')

    @computed_field
    @property
    def major(self) -> int:
        return int(self.version.split('.')[0])

    @computed_field
    @property
    def minor(self) -> int:
        return int(self.version.split('.')[1])

    @computed_field
    @property
    def patch(self) -> int:
        return int(self.version.split('.')[2])
