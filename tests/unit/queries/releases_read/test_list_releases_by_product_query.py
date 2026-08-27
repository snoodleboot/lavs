"""Unit tests for :class:`ListReleasesByProductQuery` against isolated DuckDB."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.errors.not_found_error import NotFoundError
from app.queries.products.product_id_request import ProductIdRequest
from app.queries.releases_read.list_releases_by_product_query import (
    ListReleasesByProductQuery,
)

_DDL = """
CREATE TABLE products (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    base_version VARCHAR NOT NULL DEFAULT '0.0.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE components (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    name VARCHAR NOT NULL,
    kind VARCHAR NOT NULL CHECK (kind IN ('library', 'service', 'ui', 'cli'))
);
CREATE TABLE versions (
    id VARCHAR PRIMARY KEY,
    component_id VARCHAR NOT NULL REFERENCES components(id),
    major INTEGER NOT NULL,
    minor INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    prerelease VARCHAR,
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE releases (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    product_version VARCHAR NOT NULL,
    label VARCHAR,
    notes VARCHAR,
    idempotency_key VARCHAR,
    bump_level VARCHAR,
    bump_rationale VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE release_components (
    release_id VARCHAR NOT NULL REFERENCES releases(id),
    component_id VARCHAR NOT NULL,
    version_id VARCHAR NOT NULL,
    change_level VARCHAR,
    PRIMARY KEY (release_id, component_id)
);
"""


def _fresh_connection() -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB carrying the release-read schema."""
    conn = duckdb.connect(":memory:")
    conn.execute(_DDL)
    return conn


def _seed_product(conn: duckdb.DuckDBPyConnection, product_id: str) -> None:
    """Insert a product row."""
    conn.execute(
        "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
        (product_id, "Aurora Platform", None),
    )


def _seed_component(conn: duckdb.DuckDBPyConnection, component_id: str, name: str) -> None:
    """Insert a component row under the seeded product."""
    conn.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, "prod-1", name, "service"),
    )


def _seed_version(
    conn: duckdb.DuckDBPyConnection,
    version_id: str,
    component_id: str,
    major: int,
    minor: int,
    patch: int,
    prerelease: str | None = None,
) -> None:
    """Insert a version row for a component."""
    conn.execute(
        "INSERT INTO versions (id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (version_id, component_id, major, minor, patch, prerelease, "active"),
    )


def _seed_release(
    conn: duckdb.DuckDBPyConnection,
    release_id: str,
    product_version: str,
    created_at: str,
    label: str | None = None,
    notes: str | None = None,
) -> None:
    """Insert a release row with an explicit ``created_at`` timestamp."""
    conn.execute(
        "INSERT INTO releases (id, product_id, product_version, label, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (release_id, "prod-1", product_version, label, notes, created_at),
    )


def _pin(
    conn: duckdb.DuckDBPyConnection, release_id: str, component_id: str, version_id: str
) -> None:
    """Pin a component version into a release manifest."""
    conn.execute(
        "INSERT INTO release_components (release_id, component_id, version_id) VALUES (?, ?, ?)",
        (release_id, component_id, version_id),
    )


class TestListReleasesByProductQuery(IsolatedAsyncioTestCase):
    """Behaviour of the product release-ledger read query."""

    async def test_orders_releases_newest_first_with_id_tiebreak(self) -> None:
        """Releases come back ``created_at`` desc, then ``id`` desc on ties."""
        # Arrange
        conn = _fresh_connection()
        _seed_product(conn, "prod-1")
        _seed_release(conn, "rel-a", "5.1.0", "2026-06-29T12:00:00")
        _seed_release(conn, "rel-b", "5.2.0", "2026-06-30T12:00:00")
        # Two releases share a timestamp; id desc breaks the tie.
        _seed_release(conn, "rel-c", "5.3.0", "2026-06-30T12:00:00")

        # Act
        result = await ListReleasesByProductQuery().apply(
            ProductIdRequest(product_id="prod-1"), conn
        )

        # Assert
        assert [release.id for release in result] == ["rel-c", "rel-b", "rel-a"]

    async def test_each_release_carries_its_frozen_manifest(self) -> None:
        """Every release carries its own pinned manifest, name + version string."""
        # Arrange
        conn = _fresh_connection()
        _seed_product(conn, "prod-1")
        _seed_component(conn, "comp-a", "lavs-api")
        _seed_component(conn, "comp-b", "lavs-ui")
        _seed_version(conn, "v-a-1", "comp-a", 2, 4, 0)
        _seed_version(conn, "v-b-1", "comp-b", 0, 9, 0, prerelease="rc.1")
        _seed_release(conn, "rel-a", "5.1.0", "2026-06-29T12:00:00")
        _pin(conn, "rel-a", "comp-a", "v-a-1")
        _pin(conn, "rel-a", "comp-b", "v-b-1")

        # Act
        result = await ListReleasesByProductQuery().apply(
            ProductIdRequest(product_id="prod-1"), conn
        )

        # Assert
        assert len(result) == 1
        manifest = result[0].components
        # Ordered by component name: lavs-api before lavs-ui.
        assert [entry.name for entry in manifest] == ["lavs-api", "lavs-ui"]
        assert manifest[0].version_id == "v-a-1"
        assert manifest[0].version == "2.4.0"
        assert manifest[1].version == "0.9.0-rc.1"

    async def test_known_product_with_no_releases_returns_empty_list(self) -> None:
        """A product that exists but has no releases yields ``[]``."""
        # Arrange
        conn = _fresh_connection()
        _seed_product(conn, "prod-1")

        # Act
        result = await ListReleasesByProductQuery().apply(
            ProductIdRequest(product_id="prod-1"), conn
        )

        # Assert
        assert result == []

    async def test_unknown_product_raises_not_found(self) -> None:
        """An unknown product id raises :class:`NotFoundError`."""
        # Arrange
        conn = _fresh_connection()

        # Act / Assert
        with self.assertRaises(NotFoundError) as caught:
            await ListReleasesByProductQuery().apply(ProductIdRequest(product_id="ghost"), conn)
        assert caught.exception.details["product_id"] == "ghost"
