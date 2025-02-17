import contextlib
from typing import Any

from app.connections.duckdb_connection import DuckDBConnection


class ConnectionFactory:
    __registry = {"duckdb": DuckDBConnection}

    def retrieve(self, key) -> Any:

        return self.__registry[key]().connection
