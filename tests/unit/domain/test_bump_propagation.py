"""Unit tests for the pure DAG bump propagation and product-bump derivation."""

from app.domain.bump_propagation import (
    derive_product_bump,
    effective_levels,
    max_level,
    propagate,
)
from app.models.enums.bump_level import BumpLevel


def test_max_level_of_empty_is_none() -> None:
    """The maximum of no levels is NONE (the identity)."""
    # Assert
    assert max_level([]) is BumpLevel.NONE


def test_max_level_picks_highest_ordinal() -> None:
    """max_level orders NONE < PATCH < MINOR < MAJOR."""
    # Assert
    assert max_level([BumpLevel.PATCH, BumpLevel.MAJOR, BumpLevel.MINOR]) is BumpLevel.MAJOR
    assert max_level([BumpLevel.NONE, BumpLevel.PATCH]) is BumpLevel.PATCH


def test_propagation_is_contraction() -> None:
    """P never raises a dependent above its dependency; MAJOR -> MINOR, MINOR -> PATCH."""
    # Assert
    assert propagate(BumpLevel.NONE) is BumpLevel.NONE
    assert propagate(BumpLevel.PATCH) is BumpLevel.PATCH
    assert propagate(BumpLevel.MINOR) is BumpLevel.PATCH
    assert propagate(BumpLevel.MAJOR) is BumpLevel.MINOR


def test_worked_example_effective_levels() -> None:
    """The plan's §7a worked graph yields the documented per-node effective levels.

    Graph: API -> Core, CLI -> API, Docs (no edges). Core changed MAJOR; the rest
    are NONE (Docs PATCH).
    """
    # Arrange
    own = {
        "core": BumpLevel.MAJOR,
        "api": BumpLevel.NONE,
        "cli": BumpLevel.NONE,
        "docs": BumpLevel.PATCH,
    }
    edges = [("api", "core"), ("cli", "api")]

    # Act
    effective = effective_levels(own, edges)

    # Assert
    assert effective["core"] is BumpLevel.MAJOR
    assert effective["api"] is BumpLevel.MINOR  # max(NONE, P(MAJOR)=MINOR)
    assert effective["cli"] is BumpLevel.PATCH  # max(NONE, P(MINOR)=PATCH)
    assert effective["docs"] is BumpLevel.PATCH


def test_removed_dependency_endpoint_propagates_as_major() -> None:
    """An edge into a removed (inactive) endpoint feeds P(MAJOR)=MINOR to its dependent (G-P9h)."""
    # Arrange: 'gone' is referenced by an edge but has no own level (removed).
    own = {"app": BumpLevel.NONE}
    edges = [("app", "gone")]

    # Act
    effective = effective_levels(own, edges)

    # Assert
    assert effective["gone"] is BumpLevel.MAJOR
    assert effective["app"] is BumpLevel.MINOR


def test_diamond_graph_terminates_and_maxes() -> None:
    """A diamond dependency resolves without infinite recursion."""
    # Arrange: top -> left, top -> right, left -> base, right -> base.
    own = {
        "top": BumpLevel.NONE,
        "left": BumpLevel.NONE,
        "right": BumpLevel.NONE,
        "base": BumpLevel.MAJOR,
    }
    edges = [("top", "left"), ("top", "right"), ("left", "base"), ("right", "base")]

    # Act
    effective = effective_levels(own, edges)

    # Assert: base MAJOR -> left/right MINOR -> top P(MINOR)=PATCH.
    assert effective["base"] is BumpLevel.MAJOR
    assert effective["left"] is BumpLevel.MINOR
    assert effective["top"] is BumpLevel.PATCH


def test_product_bump_is_max_own_for_intra_product_graph() -> None:
    """Contraction property: the product bump equals the max own change, edges notwithstanding."""
    # Arrange
    own = {
        "core": BumpLevel.MAJOR,
        "api": BumpLevel.NONE,
        "cli": BumpLevel.NONE,
        "docs": BumpLevel.PATCH,
    }
    edges = [("api", "core"), ("cli", "api")]

    # Act
    with_edges = derive_product_bump(own, edges, removed_any=False)
    without_edges = derive_product_bump(own, [], removed_any=False)

    # Assert: MAJOR from Core's own change, invariant to edge presence.
    assert with_edges is BumpLevel.MAJOR
    assert without_edges is BumpLevel.MAJOR


def test_product_bump_none_when_no_change() -> None:
    """A graph with no changes derives NONE."""
    # Assert
    assert derive_product_bump({"a": BumpLevel.NONE}, [], removed_any=False) is BumpLevel.NONE


def test_removed_component_forces_major() -> None:
    """A removed component raises the product bump to MAJOR (G-P9a)."""
    # Assert
    assert derive_product_bump({"a": BumpLevel.NONE}, [], removed_any=True) is BumpLevel.MAJOR
