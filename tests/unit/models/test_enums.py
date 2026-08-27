"""Tests for the domain enums."""

from app.models.enums.bump_level import BumpLevel
from app.models.enums.component_kind import ComponentKind
from app.models.enums.version_status import VersionStatus


def test_component_kind_values() -> None:
    """ComponentKind must expose the contract's string values."""
    # Act
    values = {member.value for member in ComponentKind}

    # Assert
    assert values == {"library", "service", "ui", "cli"}


def test_component_kind_is_string() -> None:
    """ComponentKind members must compare equal to their string value."""
    # Assert
    assert ComponentKind.SERVICE == "service"


def test_version_status_values() -> None:
    """VersionStatus must expose the contract's string values."""
    # Act
    values = {member.value for member in VersionStatus}

    # Assert
    assert values == {"active", "superseded", "rolled_back"}


def test_version_status_is_string() -> None:
    """VersionStatus members must compare equal to their string value."""
    # Assert
    assert VersionStatus.ROLLED_BACK == "rolled_back"


def test_bump_level_values() -> None:
    """BumpLevel must expose the four derived-bump magnitudes."""
    # Act
    values = {member.value for member in BumpLevel}

    # Assert
    assert values == {"none", "patch", "minor", "major"}


def test_bump_level_is_string() -> None:
    """BumpLevel members must compare equal to their string value."""
    # Assert
    assert BumpLevel.MAJOR == "major"
