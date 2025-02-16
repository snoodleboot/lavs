import logging
import traceback

from app.connections.connection_factory import ConnectionFactory
from app.queries.versions.retrieve_latest_version import retrieve_latest_version


async def delete_version(product_name: str, major: int, minor: int, patch: int) -> bool:
    logger = logging.getLogger()

    try:
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            result = await retrieve_latest_version(product_name=product_name)
            _ = conn.sql(
                query=(
                    f"DELETE FROM Versions "
                    f"WHERE product_name='{product_name}' "
                    f"AND major={major} "
                    f"AND minor={minor} "
                    f"AND patch={patch}"
                )
            )
            result = await retrieve_latest_version(product_name=product_name)
        logger.info(result)
    except:
        print(traceback.format_exc())
