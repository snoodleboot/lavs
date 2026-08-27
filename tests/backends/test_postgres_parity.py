"""PostgreSQL parity: the DuckDB behaviours, re-driven over real PostgreSQL.

Every test here uses the ``pg_env`` fixture (see :mod:`conftest`), which resets a
throwaway PostgreSQL to a clean schema and selects the Postgres backend, then
drives the **real** HTTP surface through a lifespan-active
:class:`~fastapi.testclient.TestClient`. Because the application wiring is
backend-agnostic (the query layer speaks a single ``?``-placeholder dialect that
:class:`~app.connections.db_session.DbSession` rewrites), these tests exercise the
same routers, queries, and models the DuckDB acceptance suite proves — only the
backend beneath them changes. Green here is the P3 exit proof.

The whole module is marked :mod:`postgres`; run it with ``pytest -m postgres``.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.acceptance._auth_support import (
    login,
    signup,
    signup_and_verify,
    unique_email,
)

pytestmark = pytest.mark.postgres

_CREATED_OK = (200, 201)


@contextmanager
def _pg_client() -> Iterator[TestClient]:
    """Yield a lifespan-active client bound to the selected Postgres backend.

    The ``pg_env`` fixture must already have exported the ``LAVS_DB_BACKEND`` /
    ``LAVS_PG_*`` environment; entering the client runs the application lifespan,
    which builds the Postgres backend and materialises the schema on the clean
    database.
    """
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def _create_product(client: TestClient, name: str) -> dict[str, Any]:
    """Create a product and return its body."""
    response = client.post("/products", json={"name": name, "description": "pg-parity"})
    assert response.status_code in _CREATED_OK, response.text
    return response.json()


def _create_component(client: TestClient, product_id: str, name: str, kind: str) -> dict[str, Any]:
    """Create a component under ``product_id`` and return its body."""
    response = client.post(
        "/components", json={"product_id": product_id, "name": name, "kind": kind}
    )
    assert response.status_code in _CREATED_OK, response.text
    return response.json()


def _create_version(client: TestClient, component_id: str, version: str) -> dict[str, Any]:
    """Append an active version to a component and return its body."""
    response = client.post("/versions", json={"component_id": component_id, "version": version})
    assert response.status_code in _CREATED_OK, response.text
    return response.json()


class TestProductParity:
    """Products CRUD and the unique-name 409, on PostgreSQL."""

    def test_create_and_read_back_product(self, pg_env: Any) -> None:
        # Arrange / Act
        with _pg_client() as client:
            created = _create_product(client, "Aurora Platform")

            # Act
            fetched = client.get(f"/products/{created['id']}")
            listed = client.get("/products")

        # Assert
        assert created["name"] == "Aurora Platform"
        assert created.get("created_at"), "a product must carry a created_at timestamp"
        assert created["base_version"] == "0.0.0"
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["id"] == created["id"]
        assert any(item["id"] == created["id"] for item in listed.json())

    def test_duplicate_name_returns_409(self, pg_env: Any) -> None:
        # Arrange
        with _pg_client() as client:
            _create_product(client, "Duplicate")

            # Act
            conflict = client.post("/products", json={"name": "Duplicate"})

        # Assert
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["error"]["code"]


class TestVersionLifecycleParity:
    """Component + version lifecycle, history, and non-destructive rollback, on PostgreSQL."""

    def test_history_and_rollback_are_non_destructive(self, pg_env: Any) -> None:
        # Arrange
        with _pg_client() as client:
            product = _create_product(client, "Aurora Platform")
            component = _create_component(client, product["id"], "lavs-api", "service")
            first = _create_version(client, component["id"], "1.0.0")
            latest = _create_version(client, component["id"], "2.0.0")

            # Act
            rollback = client.post(f"/versions/{latest['id']}/rollback")
            history = client.get(f"/components/{component['id']}/versions").json()

        # Assert
        assert rollback.status_code == 200, rollback.text
        assert len(history) == 2, "rollback must preserve the full history"
        by_id = {version["id"]: version for version in history}
        assert by_id[latest["id"]]["status"] == "rolled_back"
        assert by_id[first["id"]]["status"] == "active", "the prior version must be re-activated"


class TestTimelineParity:
    """The composite product timeline renders over PostgreSQL."""

    def test_timeline_lists_component_versions(self, pg_env: Any) -> None:
        # Arrange
        with _pg_client() as client:
            product = _create_product(client, "Aurora Platform")
            component = _create_component(client, product["id"], "lavs-api", "service")
            _create_version(client, component["id"], "1.0.0")

            # Act
            timeline = client.get(f"/products/{product['id']}/timeline")

        # Assert
        assert timeline.status_code == 200, timeline.text
        body = timeline.json()
        assert body["product"]["id"] == product["id"]
        assert body["components"], "the timeline must carry the product's components"


class TestReleaseParity:
    """Release cut, frozen manifest, immutability, and idempotency, on PostgreSQL."""

    def _seed_two_components(self, client: TestClient) -> dict[str, Any]:
        product = _create_product(client, "Aurora Platform")
        api = _create_component(client, product["id"], "lavs-api", "service")
        ui = _create_component(client, product["id"], "lavs-ui", "ui")
        api_version = _create_version(client, api["id"], "2.4.0")
        ui_version = _create_version(client, ui["id"], "1.0.0")
        return {
            "product_id": product["id"],
            "api": {"component_id": api["id"], "version_id": api_version["id"]},
            "ui": {"component_id": ui["id"], "version_id": ui_version["id"]},
        }

    def test_cut_freezes_manifest_and_reads_back(self, pg_env: Any) -> None:
        # Arrange
        with _pg_client() as client:
            seed = self._seed_two_components(client)

            # Act
            cut = client.post(f"/products/{seed['product_id']}/releases", json={"label": "1.0"})
            fetched = client.get(f"/releases/{cut.json()['id']}")

        # Assert
        assert cut.status_code == 201, cut.text
        body = cut.json()
        assert body["product_version"] == "0.1.0", "first cut bumps minor from base 0.0.0"
        assert body.get("created_at"), "a release must carry a created_at timestamp"
        manifest = {entry["component_id"]: entry for entry in body["components"]}
        assert manifest[seed["api"]["component_id"]]["version_id"] == seed["api"]["version_id"]
        assert manifest[seed["ui"]["component_id"]]["version_id"] == seed["ui"]["version_id"]
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["id"] == body["id"]

    def test_second_cut_bumps_minor(self, pg_env: Any) -> None:
        # Arrange
        with _pg_client() as client:
            seed = self._seed_two_components(client)
            first = client.post(f"/products/{seed['product_id']}/releases", json={})
            assert first.json()["product_version"] == "0.1.0", first.text
            # A minor component change drives the derived minor bump (default policy, P9).
            _create_version(client, seed["api"]["component_id"], "2.5.0")

            # Act
            second = client.post(f"/products/{seed['product_id']}/releases", json={})

        # Assert
        assert second.status_code == 201, second.text
        assert second.json()["product_version"] == "0.2.0"

    def test_idempotency_key_collapses_retried_cut(self, pg_env: Any) -> None:
        # Arrange
        with _pg_client() as client:
            seed = self._seed_two_components(client)
            headers = {"Idempotency-Key": "d7c0ffee-0000-4000-8000-000000000001"}

            # Act
            first = client.post(
                f"/products/{seed['product_id']}/releases", json={"label": "once"}, headers=headers
            )
            second = client.post(
                f"/products/{seed['product_id']}/releases", json={"label": "once"}, headers=headers
            )

        # Assert
        assert first.status_code == 201, first.text
        assert second.status_code in _CREATED_OK, second.text
        assert first.json()["id"] == second.json()["id"], "a retried cut must not create a release"
        assert second.json()["product_version"] == first.json()["product_version"]


class TestAuthParity:
    """The signup -> verify -> login -> me -> logout flow, on PostgreSQL."""

    def test_full_auth_flow(self, pg_env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange -- enforce password auth on top of the already-selected PG backend.
        from tests.acceptance._auth_support import ALLOWED_DOMAIN, AUTH_MODES

        monkeypatch.setenv("LAVS_AUTH_MODES", AUTH_MODES)
        monkeypatch.setenv("LAVS_ALLOWED_EMAIL_DOMAINS", ALLOWED_DOMAIN)
        monkeypatch.delenv("LAVS_API_KEY", raising=False)
        email = unique_email()

        from app.main import app

        with TestClient(
            app, base_url="https://testserver", raise_server_exceptions=False
        ) as client:
            # Act 1 -- signup + email verification activates the user.
            verify = signup_and_verify(client, email)

            # Act 2 -- login mints a session cookie; /me reflects the user; logout revokes it.
            login_response = login(client, email)
            me_response = client.get("/auth/me")
            logout_response = client.post("/auth/logout")
            me_after_logout = client.get("/auth/me")

            # Act 3 -- a duplicate signup is a 409.
            duplicate = signup(client, email)

        # Assert
        assert verify.status_code == 200, verify.text
        assert login_response.status_code == 200, login_response.text
        assert me_response.status_code == 200, me_response.text
        assert me_response.json()["email"] == email
        assert logout_response.status_code == 204, logout_response.text
        assert me_after_logout.status_code == 401, "the session must be revoked after logout"
        assert duplicate.status_code == 409, duplicate.text
