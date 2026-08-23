"""Unit tests for the P9 derived-bump behaviour of :class:`CutReleaseQuery`.

These exercise the ``default`` bump policy (graph-derived) and confirm the
``legacy`` policy stays byte-identical to the pre-P9 minor bump.
"""

import json
from unittest import IsolatedAsyncioTestCase

from app.models.types.ulid_id import new_ulid
from app.queries.releases.cut_release_query import CutReleaseQuery
from app.queries.releases.cut_release_request import CutReleaseRequest
from tests.unit.queries.releases.release_query_fixtures import (
    make_connection,
    seed_component,
    seed_version,
)


def _seed_product(conn, bump_policy: str, base_version: str = "0.0.0") -> str:
    """Insert a product with an explicit bump policy and return its id."""
    product_id = new_ulid()
    conn.execute(
        "INSERT INTO products (id, name, base_version, bump_policy) VALUES (?, ?, ?, ?)",
        (product_id, "product", base_version, bump_policy),
    )
    return product_id


async def _cut(conn, product_id: str):
    """Cut a release for ``product_id`` and return the result."""
    return await CutReleaseQuery().execute(
        data=CutReleaseRequest(product_id=product_id), connection=conn
    )


def _supersede(conn, version_id: str) -> None:
    """Mark a version superseded so a newer active version replaces it."""
    conn.execute("UPDATE versions SET status = 'superseded' WHERE id = ?", (version_id,))


class TestCutReleaseDerivation(IsolatedAsyncioTestCase):
    """Derived-bump behaviour under the default and legacy policies."""

    async def test_default_first_cut_is_minor(self) -> None:
        """A first cut classifies every component as newly-added (MINOR)."""
        # Arrange
        conn = make_connection()
        product_id = _seed_product(conn, "default")
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 1, 0, 0)

        # Act
        result = await _cut(conn, product_id)

        # Assert
        self.assertEqual(result.release.product_version, "0.1.0")
        self.assertEqual(result.release.bump_level, "minor")
        self.assertEqual(result.release.components[0].change_level, "minor")

    async def test_default_recut_without_change_is_none(self) -> None:
        """A re-cut with no material change derives NONE and keeps the version."""
        # Arrange
        conn = make_connection()
        product_id = _seed_product(conn, "default")
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 1, 0, 0)
        await _cut(conn, product_id)

        # Act
        second = await _cut(conn, product_id)

        # Assert
        self.assertEqual(second.release.bump_level, "none")
        self.assertEqual(second.release.product_version, "0.1.0")

    async def test_default_major_change_bumps_major(self) -> None:
        """A component major change derives a product MAJOR bump."""
        # Arrange
        conn = make_connection()
        product_id = _seed_product(conn, "default")
        component_id = seed_component(conn, product_id, "api")
        first_version = seed_version(conn, component_id, 1, 0, 0)
        await _cut(conn, product_id)  # pins 1.0.0, product 0.1.0
        _supersede(conn, first_version)
        seed_version(conn, component_id, 2, 0, 0)

        # Act
        result = await _cut(conn, product_id)

        # Assert
        self.assertEqual(result.release.bump_level, "major")
        self.assertEqual(result.release.product_version, "1.0.0")
        self.assertEqual(result.release.components[0].change_level, "major")

    async def test_legacy_recut_is_minor(self) -> None:
        """The legacy policy minor-bumps on every cut regardless of change."""
        # Arrange
        conn = make_connection()
        product_id = _seed_product(conn, "legacy")
        component_id = seed_component(conn, product_id, "api")
        seed_version(conn, component_id, 1, 0, 0)
        await _cut(conn, product_id)  # 0.1.0

        # Act
        second = await _cut(conn, product_id)

        # Assert
        self.assertEqual(second.release.bump_level, "minor")
        self.assertEqual(second.release.product_version, "0.2.0")
        self.assertIsNone(second.release.components[0].change_level)

    async def test_default_edge_records_effective_without_changing_product_bump(self) -> None:
        """An edge lifts a dependent's effective level in the rationale, not the product bump."""
        # Arrange: api depends on core; core changes MAJOR, api unchanged.
        conn = make_connection()
        product_id = _seed_product(conn, "default")
        core = seed_component(conn, product_id, "core")
        api = seed_component(conn, product_id, "api")
        core_v1 = seed_version(conn, core, 1, 0, 0)
        seed_version(conn, api, 1, 0, 0)
        conn.execute(
            "INSERT INTO component_dependencies "
            "(id, product_id, from_component_id, to_component_id) VALUES (?, ?, ?, ?)",
            (new_ulid(), product_id, api, core),
        )
        await _cut(conn, product_id)  # 0.1.0
        _supersede(conn, core_v1)
        seed_version(conn, core, 2, 0, 0)

        # Act
        result = await _cut(conn, product_id)

        # Assert: product MAJOR from core's own change (edges do not raise it).
        self.assertEqual(result.release.bump_level, "major")
        self.assertEqual(result.release.product_version, "1.0.0")
        rationale = json.loads(result.release.bump_rationale)
        self.assertEqual(rationale["components"][core]["own"], "major")
        # api's own change is none, but its effective is lifted by the edge.
        self.assertEqual(rationale["components"][api]["own"], "none")
        self.assertEqual(rationale["components"][api]["effective"], "minor")
