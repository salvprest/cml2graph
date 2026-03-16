from collections.abc import Callable, Iterable

import networkx as nx

def by_layer(
    graph: nx.MultiDiGraph, layers: str | Iterable[str]
) -> nx.MultiDiGraph:
    """Subgraph induced by nodes in the given layers."""
    layers = _as_set(layers)
    keep = [n for n, d in graph.nodes(data=True) if d.get("layer") in layers]
    return graph.subgraph(keep).copy()


def by_element_type(
    graph: nx.MultiDiGraph, types: str | Iterable[str]
) -> nx.MultiDiGraph:
    """Subgraph induced by nodes of the given element types."""
    types = _as_set(types)
    keep = [n for n, d in graph.nodes(data=True) if d.get("type") in types]
    return graph.subgraph(keep).copy()


def by_relationship_type(
    graph: nx.MultiDiGraph, types: str | Iterable[str]
) -> nx.MultiDiGraph:
    """Keep all nodes but only edges whose type is in types."""
    types = _as_set(types)
    H = graph.copy()
    H.remove_edges_from(
        [
            (u, v, k)
            for u, v, k, d in H.edges(keys=True, data=True)
            if d.get("type") not in types
        ]
    )
    return H

def without_orphans(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Remove isolated nodes (degree == 0)."""
    keep = [n for n in graph if graph.degree(n) > 0]
    return graph.subgraph(keep).copy()


def get_filters() -> dict[str, Callable]:
    return {
        "by_layer": by_layer,
        "by_element_type": by_element_type,
        "by_relationship_type": by_relationship_type,
        "without_orphans": without_orphans,
    }


def _as_set(value: str | Iterable[str]) -> set[str]:
    return {value} if isinstance(value, str) else set(value)