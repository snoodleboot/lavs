"""Edge-table parity: ``component_dependencies`` behaves identically on every backend.

The P9 dependency-graph edge table is created by ``init_schema`` on every backend
(DuckDB, PostgreSQL, MySQL, SQL Server). Its product-scoped unique key and foreign
keys are declared in each dialect's own idiom, so these tests drive the *real*
constraints against real PostgreSQL, MySQL and SQL Server containers.

The inserts here are **raw, parameterized inserts that bypass the application
guard** (:class:`~app.queries.component_dependencies.add_dependency_query.AddDependencyQuery`),
so the DB constraint itself is what must fire — not the Python pre-check. The
discriminators:

* a valid edge inserts (the table exists with resolvable foreign keys);
* the same ``(product_id, from, to)`` twice **raises** (the UNIQUE key holds on
  every dialect, and its VARCHAR lengths are indexable on MySQL/SQL Server);
* the same ``from``/``to`` under **two** different products both succeed (proving
  ``product_id`` is part of the unique key — drop it and the second would raise).

Run one lane with ``pytest -m postgres`` (or ``mysql`` / ``mssql``).
"""

from typing import Any

import pytest

from app.backends.backend import Backend
from app.backends.backend_factory import BackendFactory


def _count(session: Any, table: str) -> int:
    """Return the row count of ``table``."""
    return int(session.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _seed_products_and_components(session: Any) -> None:
    """Create two products and two components (of the first) as edge endpoints."""
    session.execute("INSERT INTO products (id, name) VALUES (?, ?)", ("p1", "Product One"))
    session.execute("INSERT INTO products (id, name) VALUES (?, ?)", ("p2", "Product Two"))
    session.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        ("c-from", "p1", "from", "library"),
    )
    session.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        ("c-to", "p1", "to", "library"),
    )


def _insert_edge(session: Any, edge_id: str, product_id: str, from_id: str, to_id: str) -> None:
    """Insert an edge row directly, bypassing the application guard."""
    session.execute(
        "INSERT INTO component_dependencies "
        "(id, product_id, from_component_id, to_component_id) VALUES (?, ?, ?, ?)",
        (edge_id, product_id, from_id, to_id),
    )


def _assert_edge_parity_on(backend: Backend) -> None:
    """Init the schema and assert the edge table's constraints on ``backend``.

    Args:
        backend: The backend under test, already selected by the env fixture.
    """
    with backend.connect() as session:
        backend.init_schema(session)
        _seed_products_and_components(session)

        # (1) The table exists with resolvable FKs: a valid edge inserts.
        _insert_edge(session, "e1", "p1", "c-from", "c-to")
        assert _count(session, "component_dependencies") == 1

        # (3) The same from/to under a *different* product both hold — proving
        # product_id is in the unique key. (Run before the failing insert so a
        # non-autocommit backend's aborted transaction cannot mask it.)
        _insert_edge(session, "e3", "p2", "c-from", "c-to")
        assert _count(session, "component_dependencies") == 2

        # (2) A duplicate (product_id, from, to) is rejected by the DB itself.
        # Driver exception types differ per backend, so the common base is used.
        with pytest.raises(Exception):  # noqa: B017, PT011 - cross-driver constraint error
            _insert_edge(session, "e2", "p1", "c-from", "c-to")


@pytest.mark.postgres
def test_edge_parity_on_postgres(pg_env: Any) -> None:
    """The edge table and its constraints behave correctly on real PostgreSQL."""
    _assert_edge_parity_on(BackendFactory().create())


@pytest.mark.mysql
def test_edge_parity_on_mysql(mysql_env: Any) -> None:
    """The edge table and its constraints behave correctly on real MySQL."""
    _assert_edge_parity_on(BackendFactory().create())


@pytest.mark.mssql
def test_edge_parity_on_mssql(mssql_env: Any) -> None:
    """The edge table and its constraints behave correctly on real SQL Server."""
    _assert_edge_parity_on(BackendFactory().create())
