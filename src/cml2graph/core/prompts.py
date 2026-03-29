from collections import Counter

import networkx as nx


def summarize_graph(graph: nx.MultiDiGraph) -> str:
    """Statistical multiline string overview of a canonical graph."""
    node_types: Counter[str] = Counter(
        d.get("type", "unknown") for _, d in graph.nodes(data=True)
    )
    edge_types: Counter[str] = Counter(
        d.get("type", "unknown") for _, _, d in graph.edges(data=True)
    )

    lines = [
        f"Model: {graph.graph.get('model_id', 'unnamed')}",
        f"Nodes: {graph.number_of_nodes()}",
    ]
    for t, c in node_types.most_common():
        lines.append(f"  {t}: {c}")
    lines.append(f"Edges: {graph.number_of_edges()}")
    for t, c in edge_types.most_common():
        lines.append(f"  {t}: {c}")
    return "\n".join(lines)
