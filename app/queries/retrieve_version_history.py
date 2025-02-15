from typing import Dict, List

import duckdb

from app.utils.load_logger import load_logger


async def retrieve_version_history(product_name: str) -> List[Dict]:
    logger = load_logger()
    conn = None
    try:
        conn = duckdb.connect("test.db")
        result = (
            conn.sql(f"SELECT * FROM Versions WHERE product_name = '{product_name}'")
            .fetchdf()
            .to_dict("records")
        )
        logger.info(result)
    finally:
        print("oops...")
        if conn:
            conn.close()

    return result
