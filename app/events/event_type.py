"""Enumeration of the domain event types published on the SSE stream."""

from enum import StrEnum


class EventType(StrEnum):
    """The SSE event names from ``docs/design/API_CONTRACT.md`` §6.

    These values are the literal ``event:`` names a subscriber to
    ``GET /products/{id}/events`` receives, so they must match the contract
    exactly.
    """

    VERSION_CREATED = "version.created"
    VERSION_ROLLED_BACK = "version.rolled_back"
    RELEASE_CUT = "release.cut"
    DEPENDENCY_ADDED = "dependency.added"
    DEPENDENCY_REMOVED = "dependency.removed"
