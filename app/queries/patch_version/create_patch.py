from typing import Any

from app.models.requests.request_model import RequestModel
from app.queries.query import Query
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class CreatePatch(Query):
    def __init__(self):
        super().__init__()
        self._latest_version_query = RetrieveLatestVersion()

    async def apply(self, data: RequestModel, conn: Any):
        latest_version_result = await self._latest_version_query.execute(data=data)

        conn.sql(
            query=(
                f"INSERT INTO Versions "
                f"(major, minor, patch, product_name, id) "
                f"VALUES ({latest_version_result['major']}, {latest_version_result['minor']}, "
                f"{latest_version_result['patch'] + 1}, '{data.product_name}', nextval('version_id_seq'))"
            )
        )
        new_latest_version = await self._latest_version_query.execute(data=data)
        self._logger.info(new_latest_version)

        return new_latest_version
