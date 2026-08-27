"""Tests for the config-driven database table manifest."""

from app.configurations.configuration import load_database_config


def test_database_config_lists_core_tables() -> None:
    """database.yaml must declare every table, parents before children."""
    # Act
    config = load_database_config()
    names = [table.name for table in config.database.tables]

    # Assert
    assert names == [
        "products",
        "components",
        "versions",
        "releases",
        "release_components",
        "component_dependencies",
        "users",
        "sessions",
        "email_verification_tokens",
    ]


def test_products_table_declares_base_version_field() -> None:
    """The products table manifest must include the base_version field."""
    # Act
    config = load_database_config()
    products = next(t for t in config.database.tables if t.name == "products")
    field_names = {field.name for field in products.fields}

    # Assert
    assert "base_version" in field_names


def test_release_components_follows_releases() -> None:
    """release_components must be declared after releases so drops honour the FK."""
    # Act
    config = load_database_config()
    names = [table.name for table in config.database.tables]

    # Assert
    assert names.index("releases") < names.index("release_components")


def test_users_precede_their_child_tables() -> None:
    """sessions and email_verification_tokens must follow users so drops honour FKs."""
    # Act
    config = load_database_config()
    names = [table.name for table in config.database.tables]

    # Assert
    assert names.index("users") < names.index("sessions")
    assert names.index("users") < names.index("email_verification_tokens")


def test_component_dependencies_follows_its_parents() -> None:
    """component_dependencies must be declared after products and components so drops honour the FKs."""
    # Act
    config = load_database_config()
    names = [table.name for table in config.database.tables]

    # Assert
    assert names.index("products") < names.index("component_dependencies")
    assert names.index("components") < names.index("component_dependencies")


def test_versions_table_declares_status_field() -> None:
    """The versions table manifest must include the status field."""
    # Act
    config = load_database_config()
    versions = next(t for t in config.database.tables if t.name == "versions")
    field_names = {field.name for field in versions.fields}

    # Assert
    assert "status" in field_names
    assert "component_id" in field_names
