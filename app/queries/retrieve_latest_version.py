from typing import Dict

import duckdb

from app.utils.load_logger import load_logger


async def retrieve_latest_version(product_name: str) -> Dict:
    logger = load_logger()
    conn = None
    try:
        conn = duckdb.connect("test.db")
        result = (
            conn.sql(
                f"SELECT * FROM Versions WHERE product_name = '{product_name}' ORDER BY major DESC, minor DESC, patch DESC LIMIT 1"
            )
            .fetchdf()
            .to_dict("records")
        )
        logger.info(result)
    finally:
        print("oops...")
        if conn:
            conn.close()

    return result[0]
