"""Idempotent migration from the legacy flat ``Versions`` table to the relational schema."""

from app.backends.backend import Backend
from app.connections.db_session import DbSession
from app.database.database_manager import DatabaseManager
from app.database.migration.legacy_schema import LegacySchema
from app.models.enums.component_kind import ComponentKind
from app.models.types.ulid_id import new_ulid

# Defaults for the synthetic component created per migrated product. These are
# constant configuration values (one "default" service component per product),
# named here rather than written as bare literals at the INSERT site.
_DEFAULT_COMPONENT_NAME = "default"
_DEFAULT_COMPONENT_KIND = ComponentKind.SERVICE

# Portable introspection over ``information_schema``, understood by every
# supported backend. Table names are matched case-insensitively because DuckDB
# preserves the declared case (the legacy ``Versions`` table) while the codebase
# refers to the name in lower case.
#
# Both queries are constrained to the schema the session is actually in.
# ``information_schema`` is not so scoped on its own: on MySQL it spans every
# visible database, and on PostgreSQL and SQL Server every schema in the
# database — so without the predicate an unrelated ``versions`` table elsewhere
# on the same server can satisfy the legacy-shape check. ``{schema}`` is filled
# from :meth:`Backend.current_schema_expression`, a dialect constant.
_COLUMNS_FOR_TABLE_SQL = (
    "SELECT column_name FROM information_schema.columns "
    "WHERE lower(table_name) = lower(?) AND table_schema = {schema}"
)
_TABLE_EXISTS_SQL = (
    "SELECT 1 FROM information_schema.tables "
    "WHERE lower(table_name) = lower(?) AND table_schema = {schema} LIMIT 1"
)


class FlatToRelationalMigration:
    """Migrate legacy flat ``Versions`` rows into ``products``/``components``/``versions``.

    The migration is *inspect-then-migrate* and safe to run on every boot:

    * It only acts when a legacy-shaped table (one carrying a ``product_name``
      column) exists with rows **and** the relational ``products`` table is
      empty. Otherwise it is a no-op — so a fresh database on *any* supported
      backend (DuckDB, PostgreSQL, MySQL, SQL Server) is left untouched.
    * One :class:`product` is created per distinct ``product_name``; one
      synthetic ``default`` service :class:`component` per product; and one
      :class:`version` per legacy row, preserving ``major``/``minor``/``patch``
      and the ``status`` 1:1.
    * The legacy rows are preserved (the source table is archived under
      :attr:`LegacySchema.ARCHIVE_TABLE`, not dropped), keeping immutable
      history including duplicate semver rows.

    All data values are written through bound parameters; only schema
    identifiers (table/column names) are interpolated, and those come from the
    :class:`LegacySchema` named constants.

    The one statement whose syntax is not portable — renaming the legacy table
    out of the way — is delegated to :meth:`Backend.rename_table` rather than
    written here, because T-SQL has no ``ALTER TABLE ... RENAME TO``.
    """

    def __init__(self, backend: Backend) -> None:
        """Initialise the migration.

        Args:
            backend: The backend owning the session, used for the one operation
                whose syntax differs per dialect (the archive rename).
        """
        self._backend = backend

    def run(self, session: DbSession) -> None:
        """Run the migration against a live session.

        Args:
            session: The managed session to operate on. No ad-hoc connection is
                opened.
        """
        if not self._should_migrate(session):
            return

        legacy_rows = self._read_legacy_rows(session)
        self._archive_source_table(session)
        # Re-create the relational ``versions`` table now that the colliding
        # legacy name has been archived (``products``/``components`` already
        # exist from schema init; this fills in the freed ``versions`` slot).
        # Run on the same managed session — DuckDB allows only one writer — and
        # through the backend, so each dialect materialises its *own* schema.
        # Schema init is guarded (``IF NOT EXISTS`` / ``IF OBJECT_ID``), so
        # re-running it over the existing tables is a no-op.
        self._backend.init_schema(session)
        self._insert_relational(session, legacy_rows)

    def _table_columns(self, session: DbSession, table: str) -> list[str]:
        """Return the lower-cased column names of ``table``, or an empty list.

        Args:
            session: The live session.
            table: The table to introspect.

        Returns:
            The column names, lower-cased; empty when the table is absent.
        """
        sql = _COLUMNS_FOR_TABLE_SQL.format(schema=self._backend.current_schema_expression())
        rows = session.execute(sql, [table]).fetchall()
        return [str(row[0]).lower() for row in rows]

    def _table_exists(self, session: DbSession, table: str) -> bool:
        """Return whether ``table`` is present in the current database."""
        sql = _TABLE_EXISTS_SQL.format(schema=self._backend.current_schema_expression())
        return session.execute(sql, [table]).fetchone() is not None

    def _row_count(self, session: DbSession, table: str) -> int:
        """Return the number of rows in ``table``, or ``0`` when it is absent.

        Existence is checked through ``information_schema`` first so this never
        relies on driver-specific error handling to detect an absent table.

        Args:
            session: The live session.
            table: The table to count.

        Returns:
            The row count, or ``0`` if the table does not exist.
        """
        if not self._table_exists(session, table):
            return 0
        result = session.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(result[0]) if result is not None else 0

    def _should_migrate(self, session: DbSession) -> bool:
        """Decide whether a migration is warranted (idempotency gate).

        Migrate only when the source table is present in its *legacy* shape
        (has a ``product_name`` column), holds rows, and the relational
        ``products`` table is still empty.

        Args:
            session: The live session.

        Returns:
            True when the migration should run.
        """
        source_columns = self._table_columns(session, LegacySchema.SOURCE_TABLE)
        is_legacy_shape = LegacySchema.PRODUCT_NAME_COLUMN in source_columns
        if not is_legacy_shape:
            return False
        if self._row_count(session, LegacySchema.SOURCE_TABLE) == 0:
            return False
        return self._row_count(session, DatabaseManager.PRODUCTS_TABLE) == 0

    def _read_legacy_rows(self, session: DbSession) -> list[tuple[str, int, int, int, str | None]]:
        """Read the legacy rows needed to build the relational records.

        Args:
            session: The live session.

        Returns:
            Tuples of ``(product_name, major, minor, patch, status)`` ordered so
            output is deterministic.
        """
        rows = session.execute(
            "SELECT product_name, major, minor, patch, status "
            f"FROM {LegacySchema.SOURCE_TABLE} "
            "ORDER BY product_name, major, minor, patch"
        ).fetchall()
        return [(str(row[0]), int(row[1]), int(row[2]), int(row[3]), row[4]) for row in rows]

    def _archive_source_table(self, session: DbSession) -> None:
        """Park the legacy table aside, freeing the ``versions`` name.

        DuckDB treats table names case-insensitively, so the legacy ``Versions``
        and the relational ``versions`` share one name. Renaming the legacy
        table preserves its rows while letting the relational schema own the
        canonical name.

        The rename goes through :meth:`Backend.rename_table` because the syntax
        is dialect-specific — SQL Server has no ``ALTER TABLE ... RENAME TO`` and
        renames through ``sp_rename`` instead.

        Args:
            session: The live session.
        """
        self._backend.rename_table(session, LegacySchema.SOURCE_TABLE, LegacySchema.ARCHIVE_TABLE)

    def _insert_relational(
        self,
        session: DbSession,
        legacy_rows: list[tuple[str, int, int, int, str | None]],
    ) -> None:
        """Populate products/components/versions from the legacy rows.

        One product per distinct ``product_name``, one synthetic ``default``
        service component per product, and one version per legacy row with its
        status preserved 1:1. All values are bound parameters.

        Args:
            session: The live session.
            legacy_rows: The tuples returned by :meth:`_read_legacy_rows`.
        """
        component_id_by_product: dict[str, str] = {}

        for product_name, major, minor, patch, status in legacy_rows:
            component_id = component_id_by_product.get(product_name)
            if component_id is None:
                component_id = self._create_product_and_component(session, product_name)
                component_id_by_product[product_name] = component_id

            session.execute(
                "INSERT INTO versions "
                "(id, component_id, major, minor, patch, prerelease, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_ulid(), component_id, major, minor, patch, None, status),
            )

    def _create_product_and_component(self, session: DbSession, product_name: str) -> str:
        """Create one product and its synthetic default component.

        Args:
            session: The live session.
            product_name: The distinct legacy product name.

        Returns:
            The id of the created component (versions hang off this).
        """
        product_id = new_ulid()
        session.execute(
            "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
            (product_id, product_name, None),
        )

        component_id = new_ulid()
        session.execute(
            "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
            (component_id, product_id, _DEFAULT_COMPONENT_NAME, str(_DEFAULT_COMPONENT_KIND)),
        )
        return component_id
