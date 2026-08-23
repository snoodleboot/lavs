"""Unit tests for :class:`GetReleaseByIdQuery` against isolated DuckDB."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.errors.not_found_error import NotFoundError
from app.queries.releases_read.get_release_by_id_query import GetReleaseByIdQuery
from app.queries.releases_read.release_id_request import ReleaseIdRequest

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


def _seeded_connection() -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB seeded with one release and its manifest."""
    conn = duckdb.connect(":memory:")
    conn.execute(_DDL)
    conn.execute(
        "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
        ("prod-1", "Aurora Platform", None),
    )
    conn.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        ("comp-a", "prod-1", "lavs-api", "service"),
    )
    conn.execute(
        "INSERT INTO versions (id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("v-a-1", "comp-a", 2, 4, 0, None, "active"),
    )
    conn.execute(
        "INSERT INTO releases (id, product_id, product_version, label, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("rel-a", "prod-1", "5.1.0", "Aurora 5.1", None, "2026-06-29T12:00:00"),
    )
    conn.execute(
        "INSERT INTO release_components (release_id, component_id, version_id) VALUES (?, ?, ?)",
        ("rel-a", "comp-a", "v-a-1"),
    )
    return conn


class TestGetReleaseByIdQuery(IsolatedAsyncioTestCase):
    """Behaviour of the single-release read query."""

    async def test_returns_release_with_frozen_manifest(self) -> None:
        """A known release comes back with its fields and pinned manifest."""
        # Arrange
        conn = _seeded_connection()

        # Act
        result = await GetReleaseByIdQuery().apply(ReleaseIdRequest(release_id="rel-a"), conn)

        # Assert
        assert result.id == "rel-a"
        assert result.product_id == "prod-1"
        assert result.product_version == "5.1.0"
        assert result.label == "Aurora 5.1"
        assert result.notes is None
        assert len(result.components) == 1
        assert result.components[0].component_id == "comp-a"
        assert result.components[0].name == "lavs-api"
        assert result.components[0].version_id == "v-a-1"
        assert result.components[0].version == "2.4.0"

    async def test_unknown_release_raises_not_found(self) -> None:
        """An unknown release id raises :class:`NotFoundError`."""
        # Arrange
        conn = _seeded_connection()

        # Act / Assert
        with self.assertRaises(NotFoundError) as caught:
            await GetReleaseByIdQuery().apply(ReleaseIdRequest(release_id="ghost"), conn)
        assert caught.exception.details["release_id"] == "ghost"
