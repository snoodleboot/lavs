from typing import Any

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.queries.query import Query
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class CreateVersion(Query):
    def __init__(self):
        super().__init__()
        self._latest_version_query = RetrieveLatestVersion()

    async def apply(self, data: ApplicationAndVersionNameModel, conn: Any):
        result = conn.sql(
            query=(
                f"INSERT INTO Versions "
                f"(major, minor, patch, product_name, id) "
                f"VALUES ({data.major}, {data.minor}, {data.patch}, '{data.product_name}', nextval('version_id_seq'))"
            )
        )
        result = await self._latest_version_query.execute(data=data)
        self._logger.info(result)
        return result
