from app.connections.connection import Connection
from app.connections.duckdb_connection import DuckDBConnection


class ConnectionFactory:
    __registry = {"duckdb": DuckDBConnection}

    def retrieve(self, key: str) -> Connection:
        """Will find and retrieve a Connection object - not an instance.

        Args:
            key: identifier for the Connection to return.

        Raises:
            ValueError: When the key is not a valid key.
        """
        if self.__registry.get(key):
            return self.__registry[key]().connection
        else:
            raise ValueError
