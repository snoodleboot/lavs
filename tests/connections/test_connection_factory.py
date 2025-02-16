from unittest import TestCase

from duckdb import DuckDBPyConnection

from app.connections.connection_factory import ConnectionFactory


class TestConnectionFactory(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_retrieve(self):
        with ConnectionFactory().retrieve(key='duckdb') as conn:
            self.assertIsInstance(conn, DuckDBPyConnection)