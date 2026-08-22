"""The MySQL persistence backend — the InnoDB, networked, concurrent target.

``MySqlBackend`` mirrors :class:`~app.backends.postgres_backend.PostgresBackend`
behind the same :class:`~app.backends.backend.Backend` contract, differing only
in the driver (PyMySQL), the settings keys (``LAVS_MYSQL_*``), the SQL dialect
(``mysql/ddl.sql``), and two accommodations shared with the Postgres lane:

* :meth:`connect` opens the connection with ``autocommit`` enabled so a write is
  visible to the next statement without an explicit ``commit`` — matching the
  effective visibility DuckDB gives the commit-free query layer. Because PyMySQL
  drives statements through a cursor rather than a connection-level ``execute``,
  the raw connection is wrapped in
  :class:`~app.connections.pymysql_connection.PyMySqlConnection`, which presents
  the ``execute``-returns-fetchable shape :class:`DbSession` expects.
* :meth:`init_schema` splits the DDL into single statements because PyMySQL's
  cursor ``execute`` runs one statement at a time.
"""

import contextlib
import os
from collections.abc import Generator
from typing import Any
from urllib.parse import unquote, urlsplit

import pymysql

from app.backends.backend import Backend
from app.backends.backend_kind import BackendKind
from app.backends.backend_settings import BackendSettings
from app.backends.ddl_script import DdlScript
from app.connections.db_session import DbSession
from app.connections.param_style import ParamStyle
from app.connections.pymysql_connection import PyMySqlConnection


class MySqlBackend(Backend):
    """PyMySQL-backed MySQL backend using pyformat (``%s``) placeholders."""

    #: The dialect DDL script, relative to the ``app/database`` package.
    _DDL_RELATIVE_PATH: str = "mysql/ddl.sql"

    def __init__(self, settings: BackendSettings | None = None) -> None:
        """Initialise the backend.

        Args:
            settings: The backend settings supplying the connection parameters
                (DSN or discrete host/port/db/user/password). Defaults to
                settings read from the environment.
        """
        self._settings = settings or BackendSettings()

    @property
    def name(self) -> BackendKind:
        """Return :attr:`BackendKind.MYSQL`."""
        return BackendKind.MYSQL

    @property
    def param_style(self) -> ParamStyle:
        """Return :attr:`ParamStyle.PYFORMAT` — PyMySQL's placeholder style."""
        return ParamStyle.PYFORMAT

    @contextlib.contextmanager
    def connect(self) -> Generator[DbSession]:
        """Open a PyMySQL connection wrapped in a :class:`DbSession`.

        The connection is opened from the configured DSN (preferred) or the
        discrete host/port/db/user/password fields, put into ``autocommit`` mode
        so writes are immediately visible to later reads (matching DuckDB's
        effective behaviour for the commit-free query layer), wrapped in a
        :class:`~app.connections.pymysql_connection.PyMySqlConnection` so it
        speaks the ``execute``-returns-fetchable shape, and closed when the
        context exits.

        Yields:
            A live :class:`DbSession` over the PyMySQL connection.
        """
        connection = pymysql.connect(**self._connection_kwargs())
        try:
            connection.autocommit(True)
            yield DbSession(PyMySqlConnection(connection), self.param_style)
        finally:
            connection.close()

    def init_schema(self, session: DbSession) -> None:
        """Materialise the schema by running each DDL statement individually.

        PyMySQL's cursor ``execute`` runs a single statement, so the script is
        split and each statement is executed in turn. Every ``CREATE TABLE`` is
        idempotent (``IF NOT EXISTS``), so this is safe to run on every boot.

        Args:
            session: A live session to run the DDL on.
        """
        for statement in DdlScript(self.dialect_ddl()).statements():
            session.execute(statement)

    def current_schema_expression(self) -> str:
        """Return ``DATABASE()`` — MySQL's schemas *are* its databases.

        ``current_schema()`` does not exist in MySQL; the current database is the
        schema, and ``information_schema.tables.table_schema`` holds its name.
        """
        return "DATABASE()"

    def dialect_ddl(self) -> str:
        """Return the MySQL DDL script contents."""
        database_package = os.path.dirname(os.path.dirname(__file__))
        ddl_path = os.path.join(database_package, "database", self._DDL_RELATIVE_PATH)
        with open(ddl_path, encoding="utf-8") as stream:
            return stream.read()

    def _connection_kwargs(self) -> dict[str, Any]:
        """Build the PyMySQL connection keyword arguments from the settings.

        A configured DSN supersedes the discrete fields entirely; otherwise the
        host, port, database, user, and password are supplied individually, each
        omitted when unset so PyMySQL falls back to its own defaults.

        Returns:
            The keyword arguments for :func:`pymysql.connect`.
        """
        dsn = self._settings.mysql_dsn()
        if dsn is not None:
            return self._kwargs_from_dsn(dsn)

        kwargs: dict[str, Any] = {
            "host": self._settings.mysql_host(),
            "port": self._settings.mysql_port(),
        }
        database = self._settings.mysql_db()
        if database is not None:
            kwargs["database"] = database
        user = self._settings.mysql_user()
        if user is not None:
            kwargs["user"] = user
        password = self._settings.mysql_password()
        if password is not None:
            kwargs["password"] = password
        return kwargs

    def _kwargs_from_dsn(self, dsn: str) -> dict[str, Any]:
        """Parse a URL-style MySQL DSN into PyMySQL connection kwargs.

        PyMySQL, unlike psycopg, has no native DSN parameter, so a
        ``mysql://user:password@host:port/database`` URL is decomposed into the
        discrete keyword arguments PyMySQL accepts. Each component is included
        only when the URL supplies it so PyMySQL keeps its own defaults for the
        rest.

        Args:
            dsn: A URL-style MySQL DSN.

        Returns:
            The keyword arguments for :func:`pymysql.connect`.
        """
        parts = urlsplit(dsn)
        kwargs: dict[str, Any] = {}
        if parts.hostname:
            kwargs["host"] = parts.hostname
        if parts.port is not None:
            kwargs["port"] = parts.port
        if parts.username:
            kwargs["user"] = unquote(parts.username)
        if parts.password:
            kwargs["password"] = unquote(parts.password)
        database = parts.path.lstrip("/")
        if database:
            kwargs["database"] = database
        return kwargs
