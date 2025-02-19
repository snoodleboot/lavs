from typing import Any

from app.models.requests.application_and_version_model import ApplicationAndVersionNameModel
from app.models.requests.request_model import RequestModel
from app.queries.query import Query
from app.queries.versions.delete_version import DeleteVersion
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class RollbackToPreviousPatchVersion(Query):
    def __init__(self):
        super().__init__()
        self._latest_version_query = RetrieveLatestVersion()
        self._delete_version_query = DeleteVersion()

    async def apply(self, data: ApplicationAndVersionNameModel, conn: Any):
        latest_version_result = await self._latest_version_query.execute(data=data)
        _ = await self._delete_version_query.execute(data=data)
        previous_version = await self._latest_version_query.execute(data=data)
        return previous_version
