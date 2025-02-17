from unittest import TestCase

from app.connections.duckdb_connection import DuckDBConnection


class TestConnectionFactory(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_connect(self):
        connection = DuckDBConnection()
        with connection.connection as conn:
            pass