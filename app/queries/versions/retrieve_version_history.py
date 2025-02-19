from typing import Any

from app.models.requests.request_model import RequestModel
from app.queries.query import Query


class RetrieveVersionHistory(Query):
    def __init__(self):
        super().__init__()

    async def apply(self, data: RequestModel, conn: Any):
        result = (
            conn.sql(
                f"SELECT * FROM Versions WHERE product_name = '{data.product_name}'"
            )
            .fetchdf()
            .to_dict("records")
        )
        self._logger.info(result)
        return result
