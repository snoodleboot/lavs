"""Acceptance: read the release ledger and a single release manifest (P2, API_CONTRACT §5).

After cutting, the ledger ``GET /products/{id}/releases`` lists releases
**newest first**, and ``GET /releases/{id}`` returns that same frozen manifest.
The Constellation view (API_CONTRACT §7) reads both to render the ledger and a
selected release.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the release resource lane is merged the endpoints 404, so these
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

    Under the default bump policy this real change is what drives a derived bump
    on the next cut.

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


class TestReleaseManifestRead:
    """P2: the ledger lists releases newest-first and a single release reads back identically."""

    def test_ledger_lists_releases_newest_first(self, client: TestClient) -> None:
        """``GET /products/{id}/releases`` returns cuts ordered newest to oldest."""
        # Arrange
        product_id = _seed_released_product(client)
        first = client.post(f"/products/{product_id}/releases", json={"label": "first"})
        _add_version(client, product_id, "2.5.0")
        second = client.post(f"/products/{product_id}/releases", json={"label": "second"})
        assert first.status_code == 201 and second.status_code == 201, (first.text, second.text)

        # Act
        response = client.get(f"/products/{product_id}/releases")

        # Assert
        assert response.status_code == 200, response.text
        ledger = response.json()
        assert isinstance(ledger, list) and len(ledger) == 2
        assert ledger[0]["id"] == second.json()["id"], "newest release must come first"
        assert ledger[1]["id"] == first.json()["id"], "oldest release must come last"
        assert [entry["product_version"] for entry in ledger] == ["0.2.0", "0.1.0"]

    def test_get_release_returns_same_manifest_as_cut(self, client: TestClient) -> None:
        """``GET /releases/{id}`` returns the identical frozen manifest the cut produced."""
        # Arrange
        product_id = _seed_released_product(client)
        cut = client.post(f"/products/{product_id}/releases", json={"label": "Aurora 5.1"})
        assert cut.status_code == 201, cut.text
        created = cut.json()

        # Act
        response = client.get(f"/releases/{created['id']}")

        # Assert
        assert response.status_code == 200, response.text
        fetched = response.json()
        assert fetched["id"] == created["id"]
        assert fetched["product_id"] == created["product_id"]
        assert fetched["product_version"] == created["product_version"]
        assert fetched["label"] == created["label"]
        assert fetched["components"] == created["components"], (
            "the fetched manifest must match the manifest returned at cut time"
        )

    def test_ledger_entry_matches_single_release_read(self, client: TestClient) -> None:
        """A ledger entry pins the same manifest as its dedicated ``GET /releases/{id}`` read."""
        # Arrange
        product_id = _seed_released_product(client)
        cut = client.post(f"/products/{product_id}/releases", json={})
        assert cut.status_code == 201, cut.text
        release_id = cut.json()["id"]

        # Act
        ledger = client.get(f"/products/{product_id}/releases")
        single = client.get(f"/releases/{release_id}")

        # Assert
        assert ledger.status_code == 200 and single.status_code == 200
        ledger_entry = next(entry for entry in ledger.json() if entry["id"] == release_id)
        assert ledger_entry["product_version"] == single.json()["product_version"]
        assert ledger_entry["components"] == single.json()["components"]
