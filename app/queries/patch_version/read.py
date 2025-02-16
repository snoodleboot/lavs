import logging
from typing import Dict

import duckdb

from app.queries.versions.retrieve_latest_version import retrieve_latest_version


async def get_next_patch_version(product_name: str) -> Dict:
    logger = logging.getLogger()
    conn = None
    try:
        conn = duckdb.connect("test.db")

        latest_version_result = await retrieve_latest_version(product_name=product_name)

        latest_version_result["patch"] += 1
    finally:
        logger.error('oops')
        print("oops...")
        if conn:
            conn.close()

    return latest_version_result
