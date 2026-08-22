"""Migration parity: the flat→relational startup migration, on every real backend.

:class:`~app.database.migration.flat_to_relational_migration.FlatToRelationalMigration`
runs unconditionally on every boot (``app.main`` lifespan, straight after
``init_schema``) for *every* backend, but it was written when DuckDB and PostgreSQL
were the only targets. Two of its steps are dialect-sensitive:

* archiving the legacy table — SQL Server has no ``ALTER TABLE ... RENAME TO`` and
  renames through ``sp_rename``; and
* re-materialising the relational schema afterwards, which must use the *running
  backend's* DDL rather than DuckDB's.

These tests drive the real migration against real PostgreSQL, MySQL and SQL Server
containers, so both stay honest. Each test seeds a legacy-shaped flat table, runs
schema init plus the migration exactly as boot does, and asserts the relational
result — including that the legacy rows are archived rather than dropped.

Run one lane with ``pytest -m postgres`` (or ``mysql`` / ``mssql``).
"""

from typing import Any

import pytest

from app.backends.backend import Backend
from app.backends.backend_factory import BackendFactory
from app.database.migration.flat_to_relational_migration import FlatToRelationalMigration
from app.database.migration.legacy_schema import LegacySchema

#: A legacy flat ``versions`` table, in DDL every target dialect accepts. Lengths
#: are explicit because MySQL and SQL Server reject unbounded ``VARCHAR`` in a
#: column definition.
_LEGACY_DDL = (
    f"CREATE TABLE {LegacySchema.SOURCE_TABLE} ("
    "id INTEGER, major INTEGER, minor INTEGER, patch INTEGER, "
    f"{LegacySchema.PRODUCT_NAME_COLUMN} VARCHAR(255), status VARCHAR(50))"
)

#: Legacy rows: two products, one carrying two versions (so the synthetic default
#: component is reused rather than duplicated) and a non-default status to prove
#: status survives the move 1:1.
_LEGACY_ROWS: list[tuple[int, int, int, int, str, str]] = [
    (1, 1, 0, 0, "atlas", "active"),
    (2, 1, 1, 0, "atlas", "superseded"),
    (3, 2, 0, 0, "borealis", "active"),
]


def _seed_legacy_table(session: Any) -> None:
    """Create the legacy flat table and fill it with :data:`_LEGACY_ROWS`."""
    session.execute(_LEGACY_DDL)
    for row in _LEGACY_ROWS:
        session.execute(
            f"INSERT INTO {LegacySchema.SOURCE_TABLE} "
            "(id, major, minor, patch, "
            f"{LegacySchema.PRODUCT_NAME_COLUMN}, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )


def _count(session: Any, table: str) -> int:
    """Return the row count of ``table``."""
    return int(session.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _assert_migrates_on(backend: Backend) -> None:
    """Seed a legacy table, run boot's schema-init + migration, assert the result.

    Mirrors the real startup order in ``app.main``: ``init_schema`` first, then the
    migration on the same session.

    Args:
        backend: The backend under test, already selected by the env fixture.
    """
    with backend.connect() as session:
        _seed_legacy_table(session)

        # Exactly what the lifespan does, in the same order.
        backend.init_schema(session)
        FlatToRelationalMigration(backend).run(session)

        # One product per distinct legacy product_name...
        assert _count(session, "products") == 2
        # ...one synthetic 'default' component each...
        assert _count(session, "components") == 2
        # ...and one relational version per legacy row.
        assert _count(session, "versions") == len(_LEGACY_ROWS)

        # Status is carried over 1:1, not defaulted.
        statuses = sorted(
            str(row[0]) for row in session.execute("SELECT status FROM versions").fetchall()
        )
        assert statuses == ["active", "active", "superseded"]

        # The legacy rows are archived, not dropped.
        assert _count(session, LegacySchema.ARCHIVE_TABLE) == len(_LEGACY_ROWS)

        # Re-running is a no-op: products is no longer empty, so the gate holds.
        FlatToRelationalMigration(backend).run(session)
        assert _count(session, "versions") == len(_LEGACY_ROWS)


@pytest.mark.postgres
def test_migration_parity_on_postgres(pg_env: Any) -> None:
    """The flat→relational migration runs correctly on real PostgreSQL."""
    _assert_migrates_on(BackendFactory().create())


@pytest.mark.mysql
def test_migration_parity_on_mysql(mysql_env: Any) -> None:
    """The flat→relational migration runs correctly on real MySQL."""
    _assert_migrates_on(BackendFactory().create())


@pytest.mark.mssql
def test_migration_parity_on_mssql(mssql_env: Any) -> None:
    """The flat→relational migration runs correctly on real SQL Server.

    This is the lane the migration could not previously survive: the archive step
    emitted ``ALTER TABLE ... RENAME TO``, which is not valid T-SQL.
    """
    _assert_migrates_on(BackendFactory().create())


# --- Schema qualification (#60) -------------------------------------------
#
# `information_schema` is not scoped to the current schema, so the migration's
# probes constrain `table_schema` explicitly.
#
# Constructing a case where that matters takes care. A decoy legacy table in
# another schema cannot, on its own, trick a *fully initialised* database into
# migrating: `_should_migrate` reads the row count from the current schema's
# real `versions` table, and the relational schema's foreign keys mean rows there
# imply a non-empty `products`. The reachable failure is different — the probe
# reports a table that the session cannot actually resolve, and the follow-up
# `SELECT COUNT(*)` then raises.
#
# So: plant the decoy, leave the application's own schema empty, and run the
# migration. Qualified, it is a clean no-op. Unqualified, `_table_exists` says
# "yes" about a table in someone else's schema and the count blows up.

# MySQL has no decoy test: its schemas *are* databases, and the throwaway
# container's `test` user is not granted CREATE DATABASE (it fails with
# `Access denied ... to database 'lavs_decoy'`). Faking it would mean wiring
# root credentials through the shared fixture for one assertion. The MySQL
# `DATABASE()` expression is still covered for non-regression by the three
# migration parity tests above.

#: A second schema used only to hold the decoy table.
_DECOY_SCHEMA = "lavs_decoy"


def _assert_ignores_other_schema(backend: Backend) -> None:
    """Plant a legacy-shaped table in another schema; the migration must not see it.

    Args:
        backend: The backend under test.
    """
    with backend.connect() as session:
        session.execute(f"CREATE SCHEMA {_DECOY_SCHEMA}")
        session.execute(
            f"CREATE TABLE {_DECOY_SCHEMA}.{LegacySchema.SOURCE_TABLE} ("
            "id INTEGER, major INTEGER, minor INTEGER, patch INTEGER, "
            f"{LegacySchema.PRODUCT_NAME_COLUMN} VARCHAR(255), status VARCHAR(50))"
        )
        session.execute(
            f"INSERT INTO {_DECOY_SCHEMA}.{LegacySchema.SOURCE_TABLE} "
            f"(id, major, minor, patch, {LegacySchema.PRODUCT_NAME_COLUMN}, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (1, 9, 9, 9, "decoy", "active"),
        )

        # The application's own schema is deliberately still empty. Unqualified
        # probes see the decoy and raise; qualified probes see nothing and the
        # migration is a clean no-op.
        FlatToRelationalMigration(backend).run(session)

        # Nothing was created from the decoy's data.
        backend.init_schema(session)
        assert _count(session, "products") == 0
        assert _count(session, "versions") == 0


@pytest.mark.postgres
def test_migration_ignores_other_schema_on_postgres(pg_env: Any) -> None:
    """A legacy-shaped table in another PostgreSQL schema must be invisible."""
    _assert_ignores_other_schema(BackendFactory().create())


@pytest.mark.mssql
def test_migration_ignores_other_schema_on_mssql(mssql_env: Any) -> None:
    """A legacy-shaped table in another SQL Server schema must be invisible."""
    _assert_ignores_other_schema(BackendFactory().create())
