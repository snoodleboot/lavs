import traceback
from typing import Dict

import duckdb

from app.connections.connection_factory import ConnectionFactory
from app.utils.load_logger import load_logger


async def retrieve_latest_version(product_name: str) -> Dict:
    logger = load_logger()
    try:
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            result = (
                conn.sql(
                    f"SELECT * FROM Versions WHERE product_name = '{product_name}' ORDER BY major DESC, minor DESC, patch DESC LIMIT 1"
                )
                .fetchdf()
                .to_dict("records")
            )
            logger.info(result)
    except:
        print(traceback.format_exc())

    if len(result) > 0:
        return result[0]
    else:
        return {}
