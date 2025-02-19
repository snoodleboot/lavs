from typing import Dict, Any

from app.models.requests.request_model import RequestModel
from app.queries.query import Query


class RetrieveLatestVersion(Query):
    async def apply(self, data: RequestModel, conn: Any):
        result = conn.sql(
            f"SELECT * FROM Versions WHERE product_name = '{data.product_name}' ORDER BY major DESC, minor DESC, patch DESC LIMIT 1"
        ).fetchdf().to_dict("records")
        if len(result) > 0:
            return result[0]
        else:
            return {}
