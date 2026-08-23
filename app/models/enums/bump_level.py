"""Enumeration of the derived release bump levels (P9)."""

from enum import StrEnum


class BumpLevel(StrEnum):
    """The magnitude of change a release (or a component within it) represents.

    P9 replaces the blind minor-bump with a *derived* bump: each component's
    change is classified against the previously-released manifest, and the
    product's bump is the graph-wide maximum. The ordering
    ``none < patch < minor < major`` is the semantic ordinal the derivation
    takes maxima over; the string values are what is persisted on
    ``releases.bump_level`` and ``release_components.change_level``.
    """

    NONE = "none"
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"
