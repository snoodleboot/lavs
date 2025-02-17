import logging
import traceback
from typing import Dict

import duckdb

from app.connections.connection_factory import ConnectionFactory
from app.queries.versions.retrieve_latest_version import retrieve_latest_version


async def read_current_patch(product_name: str) -> Dict:
    logger = logging.getLogger()
    try:
        latest_version_result = await retrieve_latest_version(product_name=product_name)
        return {
            'patch': latest_version_result['patch']
        }
    except:
        print(traceback.format_exc())
