from typing import Dict

import duckdb

from app.utils.load_logger import load_logger


async def retrieve_all() -> Dict:
    logger = load_logger()
    conn = None
    try:
        conn = duckdb.connect("test.db")
        result = (
            conn.sql(
                f"SELECT * FROM Versions WHERE ORDER BY major DESC, minor DESC, patch DESC"
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
