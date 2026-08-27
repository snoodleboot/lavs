"""Acceptance: an Idempotency-Key prevents a double-cut (P2, API_CONTRACT §5).

Two ``POST /products/{id}/releases`` with the **same** ``Idempotency-Key`` header
create exactly one release: the second call returns the already-created release
and the product version does NOT double-bump. A missing key or a *different* key
is a distinct request and cuts a new release.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the release resource lane is merged the endpoint 404s, so these
acceptance scenarios are expected to be RED.
"""

from fastapi.testclient import TestClient

_CREATED_OK = (200, 201)


def _seed_released_product(client: TestClient) -> str:
    """Create a product + component + active version and return the product id.

    Args:
        client: The FastAPI test client.

    Returns:
        The created product's id.
    """
    product = client.post("/products", json={"name": "Aurora Platform"})
    assert product.status_code in _CREATED_OK, product.text
    product_id = str(product.json()["id"])

    component = client.post(
        "/components", json={"product_id": product_id, "name": "lavs-api", "kind": "service"}
    )
    assert component.status_code in _CREATED_OK, component.text
    version = client.post(
        "/versions", json={"component_id": str(component.json()["id"]), "version": "2.4.0"}
    )
    assert version.status_code in _CREATED_OK, version.text
    return product_id


def _add_version(client: TestClient, product_id: str, version: str) -> None:
    """Append a new active version to the product's component.

    Under the default bump policy this real component change is what drives a
    derived bump on the next cut.

    Args:
        client: The FastAPI test client.
        product_id: The parent product id.
        version: The new semantic version string.
    """
    components = client.get(f"/products/{product_id}/components").json()
    response = client.post(
        "/versions", json={"component_id": str(components[0]["id"]), "version": version}
    )
    assert response.status_code in _CREATED_OK, response.text


class TestReleaseIdempotency:
    """P2: the Idempotency-Key header collapses a retried cut onto the same release."""

    def test_same_key_returns_the_same_release(self, client: TestClient) -> None:
        """Two cuts with one key yield one release id and one ``product_version``."""
        # Arrange
        product_id = _seed_released_product(client)
        headers = {"Idempotency-Key": "d7c0ffee-0000-4000-8000-000000000001"}

        # Act
        first = client.post(
            f"/products/{product_id}/releases", json={"label": "once"}, headers=headers
        )
        second = client.post(
            f"/products/{product_id}/releases", json={"label": "once"}, headers=headers
        )

        # Assert
        assert first.status_code == 201, first.text
        assert second.status_code in (200, 201), second.text
        assert second.json()["id"] == first.json()["id"], (
            "a repeated key must return the same release"
        )
        assert first.json()["product_version"] == "0.1.0"
        assert second.json()["product_version"] == "0.1.0", "the version must not double-bump"

    def test_same_key_does_not_create_a_second_release(self, client: TestClient) -> None:
        """The ledger holds exactly one release after a repeated-key cut."""
        # Arrange
        product_id = _seed_released_product(client)
        headers = {"Idempotency-Key": "d7c0ffee-0000-4000-8000-000000000002"}

        # Act
        client.post(f"/products/{product_id}/releases", json={}, headers=headers)
        client.post(f"/products/{product_id}/releases", json={}, headers=headers)

        # Assert
        ledger = client.get(f"/products/{product_id}/releases")
        assert ledger.status_code == 200, ledger.text
        assert len(ledger.json()) == 1, "a repeated key must not append a second release"

    def test_different_key_cuts_a_new_release(self, client: TestClient) -> None:
        """A second cut with a *different* key is a new release that bumps the version."""
        # Arrange
        product_id = _seed_released_product(client)

        # Act
        first = client.post(
            f"/products/{product_id}/releases",
            json={},
            headers={"Idempotency-Key": "d7c0ffee-0000-4000-8000-000000000003"},
        )
        _add_version(client, product_id, "2.5.0")
        second = client.post(
            f"/products/{product_id}/releases",
            json={},
            headers={"Idempotency-Key": "d7c0ffee-0000-4000-8000-000000000004"},
        )

        # Assert
        assert first.status_code == 201 and second.status_code == 201, (first.text, second.text)
        assert second.json()["id"] != first.json()["id"], "a distinct key must cut a new release"
        assert first.json()["product_version"] == "0.1.0"
        assert second.json()["product_version"] == "0.2.0"

    def test_no_key_cuts_a_new_release_each_time(self, client: TestClient) -> None:
        """Without a key, each cut is independent and bumps the version."""
        # Arrange
        product_id = _seed_released_product(client)

        # Act
        first = client.post(f"/products/{product_id}/releases", json={})
        _add_version(client, product_id, "2.5.0")
        second = client.post(f"/products/{product_id}/releases", json={})

        # Assert
        assert first.status_code == 201 and second.status_code == 201, (first.text, second.text)
        assert second.json()["id"] != first.json()["id"]
        assert [first.json()["product_version"], second.json()["product_version"]] == [
            "0.1.0",
            "0.2.0",
        ]
