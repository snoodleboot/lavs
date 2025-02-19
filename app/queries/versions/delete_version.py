from typing import Any

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.queries.query import Query
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class DeleteVersion(Query):
    def __init__(self):
        super().__init__()
        self._latest_version_query = RetrieveLatestVersion()

    async def apply(self, data: ApplicationAndVersionNameModel, conn: Any):
        _ = conn.sql(
            query=(
                f"DELETE FROM Versions "
                f"WHERE product_name='{data.product_name}' "
                f"AND major={data.major} "
                f"AND minor={data.minor} "
                f"AND patch={data.patch
                }"
            )
        )
        result = await self._latest_version_query.execute(data=data)

        self._logger.info(result)
        return result
