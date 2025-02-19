import contextlib
import os

import duckdb

from app.configurations.configuration import Configuration
from app.configurations.root_dir import root_dir
from app.connections.connection import Connection


class DuckDBConnection(Connection):

    @property
    @contextlib.contextmanager
    def connection(self):
        """Generates and 'yields' a live DuckDB connection."""
        connection = None
        try:
            connection = duckdb.connect(os.path.join(root_dir(), Configuration().database_name))
            yield connection
        finally:
            if connection:
                connection.close()
