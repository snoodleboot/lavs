import logging
from typing import Dict

import duckdb


async def create_version(product_name: str, major: int, minor: int, patch: int) -> Dict:
    logger = logging.getLogger()
    conn = None
    try:
        conn = duckdb.connect("test.db")
        result = (
            conn.sql(
                (
                    f"INSERT INTO Versions "
                    f"(major, minor, patch, product_name, id) "
                    f"VALUES ({major}, {minor}, {patch}, '{product_name}', nextval('version_id_seq'))"
                )
            )
            .fetchdf()
            .to_dict("results")
        )
        logger.info(result)
    finally:
        print("oops...")
        if conn:
            conn.close()

    return result
