import os

from app.connections.connection_factory import ConnectionFactory


class DatabaseManager:

    @classmethod
    def create_table(cls):

        with ConnectionFactory().retrieve(key = 'duckdb') as conn:
            with open(os.path.join(os.path.dirname(__file__),"duckdb/ddl.sql"), "r") as stream:
                query = "".join(stream.readlines())

            conn.execute(query=query)

            _ = conn.execute("SELECT COUNT(*) as COUNT FROM Versions").fetchdf()

            assert 'Versions' in conn.execute("SHOW ALL TABLES").fetchdf().name.values

    @classmethod
    def drop_table(cls):
        with ConnectionFactory().retrieve(key = 'duckdb') as conn:
            if 'Versions' in conn.execute("SHOW ALL TABLES").fetchdf().name.values:
                conn.execute(
                    query='DROP TABLE Versions'
                )

            conn.execute(query="DROP SEQUENCE IF EXISTS version_id_seq")

            assert 'Versions' not in conn.execute("SHOW ALL TABLES").fetchdf().name.values
