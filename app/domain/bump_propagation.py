"""Pure derivation of the product bump over the intra-product dependency DAG.

Given each active component's own change level and the product's dependency
edges (``from`` depends on ``to``), this computes an *effective* level per
component — the maximum of its own level and the propagated contribution of its
dependencies — and then the product bump as the graph-wide maximum.

The propagation policy is **contraction-only** (``P(x) <= x`` for every level):
a dependency's MAJOR lifts a dependent to at most MINOR, a MINOR/PATCH to at most
PATCH. A consequence (see ``docs/planning/P9_MULTIAGENT_EXECUTION_PLAN.md`` §7a):
for an *intra-product* graph the product bump equals the maximum own change,
because every dependency is itself an active component already counted in that
maximum. The edges therefore drive per-component ``change_level``, the rationale,
and the ``/impact`` endpoint — not the product version. Propagation becomes
load-bearing on the version only in P10 (cross-product composition).

Everything here is pure: it takes already-fetched levels and edge pairs, never a
database connection, so the arithmetic unit-tests in isolation.
"""

from app.models.enums.bump_level import BumpLevel

#: Semantic ordinal of each level; maxima are taken over this ordering.
_ORDER: dict[BumpLevel, int] = {
    BumpLevel.NONE: 0,
    BumpLevel.PATCH: 1,
    BumpLevel.MINOR: 2,
    BumpLevel.MAJOR: 3,
}
_BY_ORDINAL: dict[int, BumpLevel] = {ordinal: level for level, ordinal in _ORDER.items()}

#: Propagation contribution ``P``: a dependency's effective level as felt by its
#: dependent. Contraction-only — never raises a dependent above its dependency.
_PROPAGATION: dict[BumpLevel, BumpLevel] = {
    BumpLevel.NONE: BumpLevel.NONE,
    BumpLevel.PATCH: BumpLevel.PATCH,
    BumpLevel.MINOR: BumpLevel.PATCH,
    BumpLevel.MAJOR: BumpLevel.MINOR,
}


def max_level(levels: list[BumpLevel]) -> BumpLevel:
    """Return the highest of ``levels`` by semantic ordinal (empty -> ``NONE``)."""
    highest = 0
    for level in levels:
        highest = max(highest, _ORDER[level])
    return _BY_ORDINAL[highest]


def propagate(level: BumpLevel) -> BumpLevel:
    """Return the contribution ``P(level)`` a dependency makes to its dependent."""
    return _PROPAGATION[level]


def effective_levels(
    own_levels: dict[str, BumpLevel],
    edges: list[tuple[str, str]],
) -> dict[str, BumpLevel]:
    """Compute the effective level of every node in the dependency graph.

    ``effective(n) = max(base(n), max over edges n->d of P(effective(d)))``.

    Args:
        own_levels: The own change level of each active component, keyed by id.
        edges: ``(from_id, to_id)`` pairs, meaning ``from`` depends on ``to``.

    Returns:
        The effective level of every node — active components plus any edge
        endpoint. An endpoint with no active version (removed since the prior
        manifest) has base ``MAJOR`` (G-P9h), so the result is total over all
        loaded edges and no lookup is undefined.
    """
    dependencies: dict[str, list[str]] = {node: [] for node in own_levels}
    for from_id, to_id in edges:
        dependencies.setdefault(from_id, [])
        dependencies.setdefault(to_id, [])
        dependencies[from_id].append(to_id)

    base: dict[str, BumpLevel] = {
        node: own_levels.get(node, BumpLevel.MAJOR) for node in dependencies
    }
    memo: dict[str, BumpLevel] = {}
    visiting: set[str] = set()

    def effective(node: str) -> BumpLevel:
        if node in memo:
            return memo[node]
        if node in visiting:
            # Defensive: edges are DAG-guaranteed at insert time, so this branch
            # is unreachable in practice; on a back-edge we drop the cyclic
            # contribution rather than recurse forever.
            return base[node]
        visiting.add(node)
        contributions = [propagate(effective(dependency)) for dependency in dependencies[node]]
        result = max_level([base[node], *contributions])
        visiting.discard(node)
        memo[node] = result
        return result

    return {node: effective(node) for node in dependencies}


def derive_product_bump(
    own_levels: dict[str, BumpLevel],
    edges: list[tuple[str, str]],
    removed_any: bool,
) -> BumpLevel:
    """Derive the product bump as the graph-wide maximum effective level.

    Args:
        own_levels: The own change level of each active component, keyed by id.
        edges: ``(from_id, to_id)`` dependency pairs.
        removed_any: Whether any component present in the prior manifest is
            absent from the active set (a breaking removal, G-P9a).

    Returns:
        The product bump: the max effective level over the active components,
        raised to ``MAJOR`` when a component was removed.
    """
    effective = effective_levels(own_levels, edges)
    levels = [effective[component] for component in own_levels]
    if removed_any:
        levels.append(BumpLevel.MAJOR)
    return max_level(levels)
