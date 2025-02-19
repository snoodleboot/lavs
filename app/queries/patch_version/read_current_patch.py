from typing import Any

from app.models.requests.request_model import RequestModel
from app.queries.query import Query
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class ReadCurrentPatch(Query):
    def __init__(self):
        super().__init__()
        self._latest_version_query = RetrieveLatestVersion()

    async def apply(self, data: RequestModel, conn: Any):
        latest_version_result = await self._latest_version_query.execute(data=data)
        return {"patch": latest_version_result["patch"]}
