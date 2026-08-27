"""Schema-level tests for the P9 dependency-graph additions (DuckDB dialect).

These run the real ``app/database/duckdb/ddl.sql`` against an in-memory database
and assert the new ``component_dependencies`` table, the new release/product
columns, the ``bump_policy`` default, and the edge-uniqueness constraint all
exist. Each assertion fails without the corresponding DDL change.
"""

import pathlib

import duckdb
import pytest

from app.models.types.ulid_id import new_ulid

_DDL_PATH = pathlib.Path(__file__).resolve().parents[3] / "app" / "database" / "duckdb" / "ddl.sql"


def _connect() -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB with the real LAVS schema applied."""
    connection = duckdb.connect(":memory:")
    connection.execute(_DDL_PATH.read_text())
    return connection


def _seed_product(connection: duckdb.DuckDBPyConnection) -> str:
    """Insert a product (without bump_policy) and return its id."""
    product_id = new_ulid()
    connection.execute("INSERT INTO products (id, name) VALUES (?, ?)", (product_id, "p"))
    return product_id


def _seed_component(connection: duckdb.DuckDBPyConnection, product_id: str, name: str) -> str:
    """Insert a component under ``product_id`` and return its id."""
    component_id = new_ulid()
    connection.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, product_id, name, "library"),
    )
    return component_id


def _columns(connection: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    """Return the lower-cased column names of ``table``."""
    rows = connection.execute(
        "SELECT column_name FROM information_schema.columns WHERE lower(table_name) = ?",
        (table,),
    ).fetchall()
    return {str(row[0]).lower() for row in rows}


def _insert_edge(
    connection: duckdb.DuckDBPyConnection,
    product_id: str,
    from_id: str,
    to_id: str,
) -> None:
    """Insert a dependency edge row."""
    connection.execute(
        "INSERT INTO component_dependencies "
        "(id, product_id, from_component_id, to_component_id) VALUES (?, ?, ?, ?)",
        (new_ulid(), product_id, from_id, to_id),
    )


def test_component_dependencies_columns_exist() -> None:
    """The edge table must carry the P9 columns."""
    # Arrange
    connection = _connect()

    # Act
    columns = _columns(connection, "component_dependencies")

    # Assert
    assert columns == {
        "id",
        "product_id",
        "from_component_id",
        "to_component_id",
        "created_at",
    }


def test_release_and_product_bump_columns_exist() -> None:
    """The derived-bump columns must be added to the existing tables."""
    # Arrange
    connection = _connect()

    # Assert
    assert {"bump_level", "bump_rationale"} <= _columns(connection, "releases")
    assert "change_level" in _columns(connection, "release_components")
    assert "bump_policy" in _columns(connection, "products")


def test_bump_policy_defaults_to_legacy() -> None:
    """A product created without bump_policy must default to 'legacy'."""
    # Arrange
    connection = _connect()
    product_id = _seed_product(connection)

    # Act
    row = connection.execute(
        "SELECT bump_policy FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    # Assert
    assert row is not None
    assert row[0] == "legacy"


def test_duplicate_edge_is_rejected() -> None:
    """The (product, from, to) unique key must forbid a duplicate edge."""
    # Arrange
    connection = _connect()
    product_id = _seed_product(connection)
    from_id = _seed_component(connection, product_id, "from")
    to_id = _seed_component(connection, product_id, "to")
    _insert_edge(connection, product_id, from_id, to_id)

    # Act / Assert
    with pytest.raises(duckdb.ConstraintException):
        _insert_edge(connection, product_id, from_id, to_id)


def test_same_edge_under_two_products_is_allowed() -> None:
    """The unique key includes product_id, so the same from/to under two products holds."""
    # Arrange
    connection = _connect()
    product_one = _seed_product(connection)
    product_two = _seed_product(connection)
    from_id = _seed_component(connection, product_one, "from")
    to_id = _seed_component(connection, product_one, "to")

    # Act
    _insert_edge(connection, product_one, from_id, to_id)
    _insert_edge(connection, product_two, from_id, to_id)

    # Assert
    count = connection.execute("SELECT COUNT(*) FROM component_dependencies").fetchone()
    assert count is not None
    assert count[0] == 2
