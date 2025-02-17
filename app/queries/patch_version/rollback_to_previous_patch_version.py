import logging
import traceback
from typing import Dict

import duckdb

from app.queries.versions.delete_version import delete_version
from app.queries.versions.retrieve_latest_version import retrieve_latest_version


async def rollback_to_previous_patch_version(product_name: str) -> Dict:
    logger = logging.getLogger()
    try:
        conn = duckdb.connect("test.db")

        latest_version_result = await retrieve_latest_version(product_name=product_name)
        _ = await delete_version(**latest_version_result)
        previous_version = await retrieve_latest_version(product_name=product_name)
        return previous_version
    except:
        print(traceback.format_exc())
