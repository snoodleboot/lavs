"""Unit tests for the SSE event-type enum."""

from app.events.event_type import EventType


def test_event_type_values_match_contract() -> None:
    """EventType must expose the §6 SSE event names exactly."""
    # Act
    values = {member.value for member in EventType}

    # Assert
    assert values == {
        "version.created",
        "version.rolled_back",
        "release.cut",
        "dependency.added",
        "dependency.removed",
    }


def test_event_type_is_string() -> None:
    """EventType members must compare equal to their wire string."""
    # Assert
    assert EventType.RELEASE_CUT == "release.cut"
