"""Unit tests for the pure dependency-graph reachability/cycle checks."""

from app.domain.dependency_graph import is_reachable, would_create_cycle


def test_is_reachable_direct_edge() -> None:
    """A direct edge makes the head reachable from the tail."""
    # Assert
    assert is_reachable([("a", "b")], start="a", target="b") is True


def test_is_reachable_transitive() -> None:
    """Reachability follows a chain of dependency edges."""
    # Assert
    assert is_reachable([("a", "b"), ("b", "c")], start="a", target="c") is True


def test_is_not_reachable_without_path() -> None:
    """An absent path yields False."""
    # Assert
    assert is_reachable([("a", "b")], start="b", target="a") is False


def test_would_create_cycle_direct_back_edge() -> None:
    """Adding b->a when a->b exists closes a two-node cycle."""
    # Assert
    assert would_create_cycle([("a", "b")], from_id="b", to_id="a") is True


def test_would_create_cycle_transitive() -> None:
    """Adding c->a when a->b->c exists closes a cycle."""
    # Assert
    assert would_create_cycle([("a", "b"), ("b", "c")], from_id="c", to_id="a") is True


def test_would_not_create_cycle_on_independent_edge() -> None:
    """A new edge with no return path does not create a cycle."""
    # Assert
    assert would_create_cycle([("a", "b")], from_id="a", to_id="c") is False
