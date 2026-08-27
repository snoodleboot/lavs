"""Enumeration of the per-product release bump policy (P9)."""

from enum import StrEnum


class BumpPolicy(StrEnum):
    """How a product derives its release bump.

    ``legacy`` reproduces the pre-P9 behaviour exactly (an unconditional minor
    bump on every cut); ``default`` derives the bump from each component's real
    change over the dependency graph. Existing products default to ``legacy``
    (the column default), so they see no behaviour change; new products are
    created ``default``.
    """

    LEGACY = "legacy"
    DEFAULT = "default"
