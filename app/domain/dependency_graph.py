"""Pure reachability checks for the intra-product dependency DAG.

Cycle rejection is done in the application layer rather than the database so the
identical guard holds on every backend (a recursive CTE would need a T-SQL
rewrite). These helpers take already-fetched ``(from, to)`` edge pairs — where an
edge ``from -> to`` means *from depends on to* — and never touch a connection, so
they unit-test in isolation.
"""


def _adjacency(edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Build a ``from -> [to, ...]`` dependency adjacency map from edge pairs."""
    adjacency: dict[str, list[str]] = {}
    for from_id, to_id in edges:
        adjacency.setdefault(from_id, []).append(to_id)
    return adjacency


def is_reachable(edges: list[tuple[str, str]], start: str, target: str) -> bool:
    """Return whether ``target`` is reachable from ``start`` following dependencies.

    Args:
        edges: Existing ``(from, to)`` edges (``from`` depends on ``to``).
        start: The node to search from.
        target: The node to search for.

    Returns:
        True when a path ``start ⇝ target`` exists (trivially true when
        ``start == target``).
    """
    adjacency = _adjacency(edges)
    stack = [start]
    seen: set[str] = set()
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adjacency.get(node, []))
    return False


def would_create_cycle(edges: list[tuple[str, str]], from_id: str, to_id: str) -> bool:
    """Return whether adding edge ``from_id -> to_id`` would close a cycle.

    Adding ``from -> to`` (from depends on to) closes a cycle exactly when ``to``
    can already reach ``from`` over the existing dependency edges.

    Args:
        edges: The product's existing dependency edges.
        from_id: The dependent component (the edge's tail).
        to_id: The dependency component (the edge's head).

    Returns:
        True when the new edge would introduce a cycle.
    """
    return is_reachable(edges, start=to_id, target=from_id)
