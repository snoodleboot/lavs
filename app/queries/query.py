import traceback
from logging import getLogger
from typing import Any

from app.configurations.configuration import Configuration
from app.connections.connection_factory import ConnectionFactory
from app.models.requests.request_model import RequestModel


class Query:
    def __init__(self):
        self._logger = getLogger(Configuration().application_name)

    async def execute(self, data: RequestModel):
        try:
            with ConnectionFactory().retrieve(key="duckdb") as conn:
                await self.apply(data, conn)
        except:
            self._logger.error(traceback.format_exc())
            raise

    async def apply(self, data: RequestModel, conn: Any):
        raise NotImplementedError
