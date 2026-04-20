from collections.abc import Iterable

import networkx as nx

def by_stereotype(graph: nx.MultiDiGraph, stereotypes: str | Iterable[str], exclude: bool = False) -> nx.MultiDiGraph:
    """Filter nodes by stereotype. If exclude=False (default), keep only matching nodes. If exclude=True, remove matching nodes."""
    selected = _as_set(stereotypes)
    if exclude:
        nodes = [n for n, d in graph.nodes(data=True)
                 if d.get("stereotype") not in selected]
    else:
        nodes = [n for n, d in graph.nodes(data=True)
                 if d.get("stereotype") in selected]
    return graph.subgraph(nodes).copy()


def by_category(graph: nx.MultiDiGraph, categories: str | Iterable[str], exclude: bool = False) -> nx.MultiDiGraph:
    """Filter nodes by category. If exclude=False (default), keep only matching nodes. If exclude=True, remove matching nodes."""
    selected = _as_set(categories)
    if exclude:
        nodes = [n for n, d in graph.nodes(data=True)
                 if d.get("category") not in selected]
    else:
        nodes = [n for n, d in graph.nodes(data=True)
                 if d.get("category") in selected]
    return graph.subgraph(nodes).copy()


def by_relation(graph: nx.MultiDiGraph, types: str | Iterable[str], exclude: bool = False) -> nx.MultiDiGraph:
    """Filter edges by relation type. If exclude=False (default), keep only matching edges. If exclude=True, remove matching edges."""
    selected = _as_set(types)
    H = graph.copy()
    if exclude:
        to_remove = [
            (u, v, k)
            for u, v, k, d in H.edges(keys=True, data=True)
            if d.get("type") in selected
        ]
    else:
        to_remove = [
            (u, v, k)
            for u, v, k, d in H.edges(keys=True, data=True)
            if d.get("type") not in selected
        ]
    H.remove_edges_from(to_remove)
    return H


def by_generalization(graph: nx.MultiDiGraph, exclude: bool = False) -> nx.MultiDiGraph:
    """Filter generalization edges. If exclude=False (default), keep only generalization edges. If exclude=True, remove generalization edges."""
    H = graph.copy()
    if exclude:
        to_remove = [
            (u, v, k)
            for u, v, k, d in H.edges(keys=True, data=True)
            if d.get("type") == "generalization"
        ]
    else:
        to_remove = [
            (u, v, k)
            for u, v, k, d in H.edges(keys=True, data=True)
            if d.get("type") != "generalization"
        ]
    H.remove_edges_from(to_remove)
    return H


def by_nature(graph: nx.MultiDiGraph, natures: str | Iterable[str], exclude: bool = False) -> nx.MultiDiGraph:
    """Filter nodes by nature. If exclude=False (default), keep only nodes whose nature contains at least one of the values. If exclude=True, remove those nodes."""
    selected = _as_set(natures)
    if exclude:
        nodes = [
            n
            for n, d in graph.nodes(data=True)
            if not (selected & {v for v in d.get("nature", "").split(",") if v})
        ]
    else:
        nodes = [
            n
            for n, d in graph.nodes(data=True)
            if selected & {v for v in d.get("nature", "").split(",") if v}
        ]
    return graph.subgraph(nodes).copy()


def without_orphans(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Remove nodes with degree 0."""
    nodes = [n for n in graph.nodes() if graph.degree(n) > 0]
    return graph.subgraph(nodes).copy()


def exclude_node_types(graph: nx.MultiDiGraph, types: Iterable[str]) -> nx.MultiDiGraph:
    """Remove nodes whose type matches any of the selected types."""
    remove = _as_set(types)
    nodes = [n for n, d in graph.nodes(data=True)
             if d.get("type") not in remove]
    return graph.subgraph(nodes).copy()


def exclude_edge_types(graph: nx.MultiDiGraph, types: Iterable[str]) -> nx.MultiDiGraph:
    """Remove edges whose type matches any of the selected types."""
    remove = _as_set(types)
    H = graph.copy()
    to_remove = [
        (u, v, k)
        for u, v, k, d in H.edges(keys=True, data=True)
        if d.get("type") in remove
    ]
    H.remove_edges_from(to_remove)
    return H


def normalize_types(
    graph: nx.MultiDiGraph,
    class_stereotypes: Iterable[str] | None = None,
    relation_stereotypes: Iterable[str] | None = None,
    class_replacement: str = "class",
    relation_replacement: str = "relation",
) -> nx.MultiDiGraph:
    """
    Replace node/edge types with generic labels for abstracted mining.
    Mirrors the old code replace_labels_with_default function.

    - Every node whose type is in "class_stereotypes" gets its
      type and label set to "class_replacement".
    - Every edge whose type is in "relation_stereotypes" gets its
      type and label set to "relation_replacement".

    If the stereotype sets are None the built-in OntoUML sets are used.
    """
    from .utils.types import CLASS_STEREOTYPES, RELATION_STEREOTYPES as _RS

    cls_set = set(class_stereotypes) if class_stereotypes else set(CLASS_STEREOTYPES)
    rel_set = set(relation_stereotypes) if relation_stereotypes else set(_RS)

    H = graph.copy()
    for n, d in H.nodes(data=True):
        if d.get("type") in cls_set:
            d["type"] = class_replacement
            d["label"] = class_replacement

    for u, v, k, d in H.edges(keys=True, data=True):
        if d.get("type") in rel_set:
            d["type"] = relation_replacement
            d["label"] = relation_replacement

    return H


def _as_set(val: str | Iterable[str]) -> set[str]:
    if isinstance(val, str):
        return {val}
    return set(val)