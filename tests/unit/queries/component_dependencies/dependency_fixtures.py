"""Shared in-memory DuckDB helpers for the dependency-query unit tests.

Each helper builds an isolated ``:memory:`` DuckDB seeded from the real DDL so
the dependency queries run against the production schema.
"""

import pathlib

import duckdb

from app.models.types.ulid_id import new_ulid

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
_DDL_PATH = _REPO_ROOT / "app" / "database" / "duckdb" / "ddl.sql"


def make_connection() -> duckdb.DuckDBPyConnection:
    """Open an isolated in-memory DuckDB with the real LAVS schema applied."""
    connection = duckdb.connect(":memory:")
    connection.execute(_DDL_PATH.read_text())
    return connection


def seed_product(connection: duckdb.DuckDBPyConnection) -> str:
    """Insert a product and return its id."""
    product_id = new_ulid()
    connection.execute("INSERT INTO products (id, name) VALUES (?, ?)", (product_id, "product"))
    return product_id


def seed_component(connection: duckdb.DuckDBPyConnection, product_id: str, name: str) -> str:
    """Insert a component under ``product_id`` and return its id."""
    component_id = new_ulid()
    connection.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, product_id, name, "library"),
    )
    return component_id


def seed_edge(
    connection: duckdb.DuckDBPyConnection,
    product_id: str,
    from_id: str,
    to_id: str,
) -> str:
    """Insert a dependency edge and return its id."""
    edge_id = new_ulid()
    connection.execute(
        "INSERT INTO component_dependencies "
        "(id, product_id, from_component_id, to_component_id) VALUES (?, ?, ?, ?)",
        (edge_id, product_id, from_id, to_id),
    )
    return edge_id
