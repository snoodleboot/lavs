"""The SQL Server persistence backend — the networked, concurrent T-SQL target.

``MssqlBackend`` mirrors :class:`~app.backends.mysql_backend.MySqlBackend` behind
the same :class:`~app.backends.backend.Backend` contract, differing only in the
driver (pymssql), the settings keys (``LAVS_MSSQL_*``), the SQL dialect
(``mssql/ddl.sql``), and two accommodations shared with the MySQL and Postgres
lanes:

* :meth:`connect` opens the connection with ``autocommit`` enabled so a write is
  visible to the next statement without an explicit ``commit`` — matching the
  effective visibility DuckDB gives the commit-free query layer. Because pymssql
  drives statements through a cursor rather than a connection-level ``execute``,
  the raw connection is wrapped in
  :class:`~app.connections.pymssql_connection.PyMssqlConnection`, which presents
  the ``execute``-returns-fetchable shape :class:`DbSession` expects.
* :meth:`init_schema` splits the DDL into single statements because pymssql's
  cursor ``execute`` runs one batch at a time. Each SQL Server ``CREATE TABLE``
  is guarded by ``IF OBJECT_ID(...) IS NULL`` (T-SQL has no
  ``CREATE TABLE IF NOT EXISTS``), so re-running the schema is a no-op.

One further override is specific to this lane: :meth:`rename_table`, because T-SQL
has no ``ALTER TABLE ... RENAME TO`` and renames objects through ``sp_rename``.
"""

import contextlib
import os
from collections.abc import Generator
from typing import Any
from urllib.parse import unquote, urlsplit

import pymssql

from app.backends.backend import Backend
from app.backends.backend_kind import BackendKind
from app.backends.backend_settings import BackendSettings
from app.backends.ddl_script import DdlScript
from app.connections.db_session import DbSession
from app.connections.param_style import ParamStyle
from app.connections.pymssql_connection import PyMssqlConnection
from app.connections.statement_dialect import StatementDialect


class MssqlBackend(Backend):
    """pymssql-backed SQL Server backend using pyformat (``%s``) placeholders."""

    #: The dialect DDL script, relative to the ``app/database`` package.
    _DDL_RELATIVE_PATH: str = "mssql/ddl.sql"

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
        """Return :attr:`BackendKind.MSSQL`."""
        return BackendKind.MSSQL

    @property
    def param_style(self) -> ParamStyle:
        """Return :attr:`ParamStyle.PYFORMAT` — pymssql's placeholder style."""
        return ParamStyle.PYFORMAT

    @contextlib.contextmanager
    def connect(self) -> Generator[DbSession]:
        """Open a pymssql connection wrapped in a :class:`DbSession`.

        The connection is opened from the configured DSN (preferred) or the
        discrete host/port/db/user/password fields, put into ``autocommit`` mode
        so writes are immediately visible to later reads (matching DuckDB's
        effective behaviour for the commit-free query layer), wrapped in a
        :class:`~app.connections.pymssql_connection.PyMssqlConnection` so it
        speaks the ``execute``-returns-fetchable shape, and closed when the
        context exits.

        Yields:
            A live :class:`DbSession` over the pymssql connection.
        """
        connection = pymssql.connect(**self._connection_kwargs())
        try:
            yield DbSession(
                PyMssqlConnection(connection),
                self.param_style,
                StatementDialect.TSQL,
            )
        finally:
            connection.close()

    def init_schema(self, session: DbSession) -> None:
        """Materialise the schema by running each DDL statement individually.

        pymssql's cursor ``execute`` runs a single batch, so the script is split
        and each statement is executed in turn. Every ``CREATE TABLE`` is guarded
        by ``IF OBJECT_ID(...) IS NULL`` (T-SQL has no ``IF NOT EXISTS`` on
        ``CREATE TABLE``), so this is safe to run on every boot.

        Args:
            session: A live session to run the DDL on.
        """
        for statement in DdlScript(self.dialect_ddl()).statements():
            session.execute(statement)

    def rename_table(self, session: DbSession, old_name: str, new_name: str) -> None:
        """Rename a table through ``sp_rename``.

        T-SQL has no ``ALTER TABLE ... RENAME TO``; SQL Server renames objects via
        the ``sp_rename`` system stored procedure, which takes the names as string
        *values* rather than identifiers — so unlike the base implementation both
        are passed as bound parameters.

        Args:
            session: A live session to run the rename on.
            old_name: The existing table name.
            new_name: The name to rename it to.
        """
        session.execute("EXEC sp_rename ?, ?", (old_name, new_name))

    def current_schema_expression(self) -> str:
        """Return ``SCHEMA_NAME()`` — T-SQL has no ``current_schema()``.

        ``SCHEMA_NAME()`` with no argument yields the calling user's default
        schema, which is the schema ``init_schema`` materialises into (``dbo``
        for the connections this backend opens).
        """
        return "SCHEMA_NAME()"

    def dialect_ddl(self) -> str:
        """Return the SQL Server DDL script contents."""
        database_package = os.path.dirname(os.path.dirname(__file__))
        ddl_path = os.path.join(database_package, "database", self._DDL_RELATIVE_PATH)
        with open(ddl_path, encoding="utf-8") as stream:
            return stream.read()

    def _connection_kwargs(self) -> dict[str, Any]:
        """Build the pymssql connection keyword arguments from the settings.

        A configured DSN supersedes the discrete fields entirely; otherwise the
        host, port, database, user, and password are supplied individually, each
        omitted when unset so pymssql falls back to its own defaults. Autocommit
        is always enabled so writes are visible to later reads.

        Returns:
            The keyword arguments for :func:`pymssql.connect`.
        """
        dsn = self._settings.mssql_dsn()
        if dsn is not None:
            kwargs = self._kwargs_from_dsn(dsn)
        else:
            kwargs = {
                "server": self._settings.mssql_host(),
                "port": self._settings.mssql_port(),
            }
            database = self._settings.mssql_db()
            if database is not None:
                kwargs["database"] = database
            user = self._settings.mssql_user()
            if user is not None:
                kwargs["user"] = user
            password = self._settings.mssql_password()
            if password is not None:
                kwargs["password"] = password
        kwargs["autocommit"] = True
        return kwargs

    def _kwargs_from_dsn(self, dsn: str) -> dict[str, Any]:
        """Parse a URL-style SQL Server DSN into pymssql connection kwargs.

        pymssql has no native URL DSN parameter, so a
        ``mssql://user:password@host:port/database`` URL is decomposed into the
        discrete keyword arguments pymssql accepts. Each component is included
        only when the URL supplies it so pymssql keeps its own defaults for the
        rest.

        Args:
            dsn: A URL-style SQL Server DSN.

        Returns:
            The keyword arguments for :func:`pymssql.connect`.
        """
        parts = urlsplit(dsn)
        kwargs: dict[str, Any] = {}
        if parts.hostname:
            kwargs["server"] = parts.hostname
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
