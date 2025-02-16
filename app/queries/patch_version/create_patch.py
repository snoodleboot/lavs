import logging
import traceback
from typing import Dict

import duckdb

from app.connections.connection_factory import ConnectionFactory
from app.queries.versions.retrieve_latest_version import retrieve_latest_version


async def create_patch(product_name: str) -> Dict:
    logger = logging.getLogger()
    try:
        with ConnectionFactory().retrieve(key="duckdb") as conn:

            latest_version_result = await retrieve_latest_version(product_name=product_name)

            conn.sql(query=(
                    f"INSERT INTO Versions "
                    f"(major, minor, patch, product_name, id) "
                    f"VALUES ({latest_version_result['major']}, {latest_version_result['minor']}, "
                    f"{latest_version_result['patch'] + 1}, '{product_name}', nextval('version_id_seq'))"
                )
            )
            new_latest_version = await retrieve_latest_version(product_name=product_name)
            logger.info(new_latest_version)
    except:
        print(traceback.format_exc())

    return new_latest_version
