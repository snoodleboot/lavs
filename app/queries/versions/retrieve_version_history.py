import traceback
from typing import Dict, List

import duckdb

from app.connections.connection_factory import ConnectionFactory
from app.utils.load_logger import load_logger


async def retrieve_version_history(product_name: str) -> List[Dict]:
    logger = load_logger()
    conn = None
    try:
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            result = (
                conn.sql(f"SELECT * FROM Versions WHERE product_name = '{product_name}'")
                .fetchdf()
                .to_dict("records")
            )
            logger.info(result)
    except:
        print(traceback.format_exc())

    return result
