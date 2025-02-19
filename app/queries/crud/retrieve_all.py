from typing import Any

from app.models.requests.request_model import RequestModel
from app.queries.query import Query


class RetrieveAll(Query):
    def __init__(self):
        super().__init__()

    async def apply(self, data: RequestModel, conn: Any):
        result = (
            conn.sql(
                f"SELECT * FROM Versions WHERE ORDER BY major DESC, minor DESC, patch DESC"
            )
            .fetchdf()
            .to_dict("records")
        )
        self._logger.info(result)
        return result
