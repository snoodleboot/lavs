import logging
from typing import Dict

import duckdb

from app.queries.retrieve_latest_version import retrieve_latest_version


async def rollback_to_previous_patch_version\
                (product_name: str) -> Dict:
    logger = logging.getLogger()
    conn = None
    try:
        conn = duckdb.connect("test.db")

        latest_version_result = await retrieve_latest_version(product_name=product_name)

        conn.sql(
            (
                f"INSERT INTO Versions "
                f"(major, minor, patch_version, product_name, id) "
                f"VALUES ({latest_version_result['major']}, {latest_version_result['minor']}, {latest_version_result['patch_version']+1}, '{product_name}', nextval('version_id_seq'))"
            )
        )
        new_latest_version = await retrieve_latest_version(product_name=product_name)
        logger.info(new_latest_version)
    finally:
        print("oops...")
        if conn:
            conn.close()

    return new_latest_version
