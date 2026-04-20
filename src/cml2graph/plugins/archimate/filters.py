from collections.abc import Callable, Iterable

import networkx as nx

def by_layer(
    graph: nx.MultiDiGraph, layers: str | Iterable[str], exclude: bool = False
) -> nx.MultiDiGraph:
    """Filter nodes by layer. If exclude=False (default), keep only matching nodes. If exclude=True, remove matching nodes."""
    selected = _as_set(layers)
    if exclude:
        keep = [n for n, d in graph.nodes(data=True) if d.get("layer") not in selected]
    else:
        keep = [n for n, d in graph.nodes(data=True) if d.get("layer") in selected]
    return graph.subgraph(keep).copy()


def by_element_type(
    graph: nx.MultiDiGraph, types: str | Iterable[str], exclude: bool = False
) -> nx.MultiDiGraph:
    """Filter nodes by element type. If exclude=False (default), keep only matching nodes. If exclude=True, remove matching nodes."""
    selected = _as_set(types)
    if exclude:
        keep = [n for n, d in graph.nodes(data=True) if d.get("type") not in selected]
    else:
        keep = [n for n, d in graph.nodes(data=True) if d.get("type") in selected]
    return graph.subgraph(keep).copy()


def by_relationship_type(
    graph: nx.MultiDiGraph, types: str | Iterable[str], exclude: bool = False
) -> nx.MultiDiGraph:
    """Filter edges by relationship type. If exclude=False (default), keep only matching edges. If exclude=True, remove matching edges."""
    selected = _as_set(types)
    H = graph.copy()
    if exclude:
        H.remove_edges_from(
            [
                (u, v, k)
                for u, v, k, d in H.edges(keys=True, data=True)
                if d.get("type") in selected
            ]
        )
    else:
        H.remove_edges_from(
            [
                (u, v, k)
                for u, v, k, d in H.edges(keys=True, data=True)
                if d.get("type") not in selected
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