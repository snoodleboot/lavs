"""Config-driven life-cycle management for the database schema."""

import os

from app.backends.backend import Backend
from app.backends.backend_factory import BackendFactory
from app.configurations.configuration import load_database_config
from app.connections.db_session import DbSession


class DatabaseManager:
    """Manage the life-cycle of the database.

    Initialisation is config-driven: the set of tables is read from
    ``database.yaml`` (via :func:`load_database_config`) while the concrete DDL
    comes from the configured backend. No table name is hardcoded here.
    """

    #: The relational root table, exposed so callers can probe migration state
    #: without re-deriving the name. Kept as a named constant rather than a bare
    #: literal at the call site.
    PRODUCTS_TABLE = "products"

    #: Portable listing of the current schema's tables. ``information_schema`` is
    #: understood by every supported backend, so this replaces DuckDB's
    #: dialect-specific ``SHOW ALL TABLES``.
    #:
    #: Constrained to the session's own schema: ``information_schema`` spans every
    #: visible database on MySQL, and every schema in the database on PostgreSQL
    #: and SQL Server. Unqualified, :meth:`drop_tables` could see a same-named
    #: table belonging to something else. ``{schema}`` is filled from
    #: :meth:`Backend.current_schema_expression`, a dialect constant.
    _LIST_TABLES_SQL = (
        "SELECT table_name FROM information_schema.tables WHERE table_schema = {schema}"
    )

    @classmethod
    def _ddl_text(cls) -> str:
        """Return the contents of the DuckDB DDL script.

        Used by :meth:`create_tables_on`, which the startup migration and the
        in-memory DuckDB unit tests call against an already-open connection.
        """
        ddl_path = os.path.join(os.path.dirname(__file__), "duckdb/ddl.sql")
        with open(ddl_path, encoding="utf-8") as stream:
            return stream.read()

    @classmethod
    def create_tables_on(cls, session: DbSession) -> None:
        """Run the DuckDB ``ddl.sql`` against an already-open session.

        Used by the startup migration, which must create tables on the managed
        session rather than opening a second connection to the same DuckDB file
        (DuckDB permits only one writer).

        Args:
            session: A live session to run the DDL on.
        """
        session.execute(cls._ddl_text())

    @classmethod
    def _table_names(cls) -> list[str]:
        """Return the configured table names from ``database.yaml``."""
        config = load_database_config()
        return [table.name for table in config.database.tables]

    @classmethod
    def _existing_tables(cls, session: DbSession, backend: Backend) -> list[str]:
        """Return the names of the tables currently present, lower-cased.

        Names are lower-cased so membership checks are case-insensitive across
        dialects (DuckDB preserves the declared case in ``information_schema``).

        Args:
            session: A live session to introspect.
            backend: The backend owning the session, supplying the dialect
                expression that scopes the listing to the current schema.
        """
        sql = cls._LIST_TABLES_SQL.format(schema=backend.current_schema_expression())
        rows = session.execute(sql).fetchall()
        return [str(row[0]).lower() for row in rows]

    @classmethod
    def create_tables(cls) -> None:
        """Create the configured tables via the configured backend.

        After running the backend's schema init, every table named in the
        configuration is verified to exist.

        Raises:
            AssertionError: When a configured table is missing after init.
        """
        backend = BackendFactory().create()
        with backend.connect() as session:
            backend.init_schema(session)

            existing = cls._existing_tables(session, backend)
            for table_name in cls._table_names():
                assert table_name in existing, f"Expected table '{table_name}' to exist after init."

    @classmethod
    def drop_tables(cls) -> None:
        """Drop each configured table if it is present.

        Tables are dropped in the reverse of their configured order so that
        child tables are removed before the parents they reference, satisfying
        foreign-key constraints.
        """
        backend = BackendFactory().create()
        with backend.connect() as session:
            existing = cls._existing_tables(session, backend)
            for table_name in reversed(cls._table_names()):
                if table_name in existing:
                    session.execute(f"DROP TABLE {table_name}")
