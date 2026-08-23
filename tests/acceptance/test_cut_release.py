"""Acceptance: cut an immutable release with a server-assigned version (P2 exit criterion).

P2 exit criterion + API_CONTRACT §5: ``POST /products/{id}/releases`` snapshots
each component's current ``active`` version into a frozen manifest and assigns
the product version itself (default bump = minor from the product's configured
base ``0.0.0``). The client may supply only an optional ``label``/``notes`` and
**cannot** set ``product_version``: the first cut of a fresh product is
``0.1.0`` and the next is ``0.2.0``.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the release/cut resource lane is merged the endpoint 404s, so these
acceptance scenarios are expected to be RED.
"""

from fastapi.testclient import TestClient

_CREATED_OK = (200, 201)


def _create_product(client: TestClient, name: str) -> dict[str, object]:
    """Register a product and return its JSON body.

    Args:
        client: The FastAPI test client.
        name: The product name to register.

    Returns:
        The parsed product response body.
    """
    response = client.post("/products", json={"name": name, "description": "acc-test"})
    assert response.status_code in _CREATED_OK, response.text
    return response.json()


def _create_component(
    client: TestClient, product_id: str, name: str, kind: str
) -> dict[str, object]:
    """Register a component under ``product_id`` and return its JSON body.

    Args:
        client: The FastAPI test client.
        product_id: The parent product id.
        name: The component name.
        kind: The component kind.

    Returns:
        The parsed component response body.
    """
    response = client.post(
        "/components", json={"product_id": product_id, "name": name, "kind": kind}
    )
    assert response.status_code in _CREATED_OK, response.text
    return response.json()


def _create_version(client: TestClient, component_id: str, version: str) -> dict[str, object]:
    """Append an immutable, now-active version to a component.

    Args:
        client: The FastAPI test client.
        component_id: The parent component id.
        version: The semantic version string.

    Returns:
        The parsed version response body.
    """
    response = client.post("/versions", json={"component_id": component_id, "version": version})
    assert response.status_code in _CREATED_OK, response.text
    return response.json()


def _add_version(client: TestClient, product_id: str, component_name: str, version: str) -> None:
    """Append a new active version to a named component of ``product_id``.

    Args:
        client: The FastAPI test client.
        product_id: The parent product id.
        component_name: The component to append the version to.
        version: The new semantic version string.
    """
    components = client.get(f"/products/{product_id}/components").json()
    component = next(entry for entry in components if entry["name"] == component_name)
    response = client.post(
        "/versions", json={"component_id": str(component["id"]), "version": version}
    )
    assert response.status_code in _CREATED_OK, response.text


def _version_string(version: dict[str, object]) -> str:
    """Render a version response as ``major.minor.patch`` with optional prerelease.

    Args:
        version: A version response body.

    Returns:
        The dotted semver string, suffixed with ``-<prerelease>`` when present.
    """
    core = f"{version['major']}.{version['minor']}.{version['patch']}"
    prerelease = version.get("prerelease")
    return f"{core}-{prerelease}" if prerelease else core


def _seed_product_with_two_components(client: TestClient) -> dict[str, object]:
    """Create a product with two components each carrying one active version.

    Args:
        client: The FastAPI test client.

    Returns:
        A dict with ``product_id`` and ``expected`` mapping each component id to
        its ``(version_id, version_string, name)`` at cut time.
    """
    product = _create_product(client, "Aurora Platform")
    product_id = str(product["id"])

    api = _create_component(client, product_id, "lavs-api", "service")
    ui = _create_component(client, product_id, "lavs-ui", "ui")
    api_version = _create_version(client, str(api["id"]), "2.4.0")
    ui_version = _create_version(client, str(ui["id"]), "1.0.0")

    expected = {
        str(api["id"]): {
            "name": "lavs-api",
            "version_id": str(api_version["id"]),
            "version": _version_string(api_version),
        },
        str(ui["id"]): {
            "name": "lavs-ui",
            "version_id": str(ui_version["id"]),
            "version": _version_string(ui_version),
        },
    }
    return {"product_id": product_id, "expected": expected}


class TestCutRelease:
    """P2 exit criterion: a cut freezes the active manifest and server-assigns the version."""

    def test_cut_returns_201_with_server_assigned_first_version(self, client: TestClient) -> None:
        """The first cut of a fresh product is ``0.1.0`` (minor bump from base ``0.0.0``)."""
        # Arrange
        seed = _seed_product_with_two_components(client)

        # Act
        response = client.post(
            f"/products/{seed['product_id']}/releases", json={"label": "Aurora 5.1"}
        )

        # Assert
        assert response.status_code == 201, (
            f"cut must return 201; got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["product_id"] == seed["product_id"]
        assert body["product_version"] == "0.1.0"
        assert isinstance(body["id"], str) and body["id"]
        assert body.get("created_at"), "a release must carry a created_at timestamp"

    def test_cut_echoes_label_and_notes(self, client: TestClient) -> None:
        """The optional ``label`` and ``notes`` are echoed back on the release."""
        # Arrange
        seed = _seed_product_with_two_components(client)

        # Act
        response = client.post(
            f"/products/{seed['product_id']}/releases",
            json={"label": "Aurora 5.1", "notes": "first public cut"},
        )

        # Assert
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["label"] == "Aurora 5.1"
        assert body["notes"] == "first public cut"

    def test_client_cannot_set_product_version(self, client: TestClient) -> None:
        """A client-supplied ``product_version`` is ignored: the server owns derivation."""
        # Arrange
        seed = _seed_product_with_two_components(client)

        # Act -- attempt to smuggle a version the server must not honour.
        response = client.post(
            f"/products/{seed['product_id']}/releases",
            json={"label": "hijack", "product_version": "9.9.9"},
        )

        # Assert -- request is accepted but the version is server-assigned, not 9.9.9.
        assert response.status_code == 201, response.text
        assert response.json()["product_version"] == "0.1.0"

    def test_cut_freezes_active_version_manifest(self, client: TestClient) -> None:
        """The frozen ``components`` manifest pins each component's active version_id + string."""
        # Arrange
        seed = _seed_product_with_two_components(client)

        # Act
        response = client.post(f"/products/{seed['product_id']}/releases", json={})

        # Assert
        assert response.status_code == 201, response.text
        components = response.json()["components"]
        assert isinstance(components, list) and len(components) == 2
        by_id = {str(entry["component_id"]): entry for entry in components}
        assert by_id.keys() == seed["expected"].keys()
        for component_id, want in seed["expected"].items():
            entry = by_id[component_id]
            assert entry["version_id"] == want["version_id"], (
                "manifest must pin the active version id"
            )
            assert entry["version"] == want["version"], (
                "manifest must record the pinned version string"
            )
            assert entry["name"] == want["name"]

    def test_second_cut_bumps_minor_to_0_2_0(self, client: TestClient) -> None:
        """A minor component change between cuts derives a minor bump ``0.1.0`` -> ``0.2.0``."""
        # Arrange
        seed = _seed_product_with_two_components(client)
        product_id = str(seed["product_id"])
        first = client.post(f"/products/{product_id}/releases", json={})
        assert first.status_code == 201, first.text
        assert first.json()["product_version"] == "0.1.0"
        # Under the default policy a minor component change drives the derived bump.
        _add_version(client, product_id, "lavs-api", "2.5.0")

        # Act
        second = client.post(f"/products/{product_id}/releases", json={})

        # Assert
        assert second.status_code == 201, second.text
        assert second.json()["product_version"] == "0.2.0"
        assert second.json()["bump_level"] == "minor"

    def test_recut_without_change_keeps_version(self, client: TestClient) -> None:
        """A re-cut with no component change derives NONE and repeats the version (G-P9d)."""
        # Arrange
        seed = _seed_product_with_two_components(client)
        product_id = str(seed["product_id"])
        first = client.post(f"/products/{product_id}/releases", json={})
        assert first.status_code == 201, first.text
        assert first.json()["product_version"] == "0.1.0"

        # Act
        second = client.post(f"/products/{product_id}/releases", json={})

        # Assert -- a distinct release row, same version, NONE bump.
        assert second.status_code == 201, second.text
        assert second.json()["id"] != first.json()["id"]
        assert second.json()["product_version"] == "0.1.0"
        assert second.json()["bump_level"] == "none"
