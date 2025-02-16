import logging
import traceback
from typing import Dict

from app.connections.connection_factory import ConnectionFactory
from app.queries.versions.retrieve_latest_version import retrieve_latest_version


async def create_version(product_name: str, major: int, minor: int, patch: int) -> Dict:
    logger = logging.getLogger()

    try:
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            result = conn.sql(
                query=(
                    f"INSERT INTO Versions "
                    f"(major, minor, patch, product_name, id) "
                    f"VALUES ({major}, {minor}, {patch}, '{product_name}', nextval('version_id_seq'))"
                )
            )
        result = await retrieve_latest_version(product_name=product_name)
        logger.info(result)
    except:
        print(traceback.format_exc())

    return result
