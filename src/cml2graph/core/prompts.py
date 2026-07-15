from collections import Counter

import networkx as nx

def summarize_graph_stat(graph: nx.MultiDiGraph) -> dict:
    """Statistical multiline string overview of a canonical graph."""
    node_types: Counter[str] = Counter(
        d.get("type", "unknown") for _, d in graph.nodes(data=True)
    )
    edge_types: Counter[str] = Counter(
        d.get("type", "unknown") for _, _, d in graph.edges(data=True)
    )

    nodes_types_stats = {}
    for t, c in node_types.most_common():
        nodes_types_stats[t] = c
    edges_types_stats = {}
    for t, c in edge_types.most_common():
        edges_types_stats[t] = c

    graph_stat_info = {
        "Model": graph.graph.get("model_id", "unnamed"),
        "Nodes": graph.number_of_nodes(),
        "Edges": graph.number_of_edges(),
        "Node Types": nodes_types_stats,
        "Edge Types": edges_types_stats,
    }
    return graph_stat_info


def summarize_graph_stat_string(graph: nx.MultiDiGraph) -> str:
    graph_stat_info = summarize_graph_stat(graph)
    # Flatten the nested dictionaries into simple "key:value" strings
    nodes_str = ", ".join(f"{k}:{v}" for k, v in graph_stat_info["Node Types"].items())
    edges_str = ", ".join(f"{k}:{v}" for k, v in graph_stat_info["Edge Types"].items())
    
    # Combine everything into a single dense line
    return (
        f"Model:{graph_stat_info['Model']} | "
        f"Nodes:{graph_stat_info['Nodes']} [{nodes_str}] | "
        f"Edges:{graph_stat_info['Edges']} [{edges_str}]"
    )