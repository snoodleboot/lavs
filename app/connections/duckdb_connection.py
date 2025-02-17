import contextlib
import os

import duckdb

from app.configurations.root_dir import root_dir
from app.connections.connection import Connection


class DuckDBConnection(Connection):

    @property
    @contextlib.contextmanager
    def connection(self):
        connection = None
        try:
            connection = duckdb.connect(os.path.join(root_dir(), "test.db"))
            yield connection
        finally:
            if connection:
                connection.close()
