import contextlib
import os
from typing import Any

import duckdb

from app.configurations.root_dir import root_dir


class ConnectionFactory:
    __registry = {
        'duckdb': lambda: duckdb.connect(os.path.join(
            root_dir(),
            "test.db"
        ))
    }

    @contextlib.contextmanager
    def retrieve(self, key) -> Any:
        connection = None
        try:
            connection = self.__registry[key]()
            yield connection
        finally:
            if connection:
                connection.close()
                # pass