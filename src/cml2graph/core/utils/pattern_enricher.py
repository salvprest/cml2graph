from collections import Counter

import networkx as nx


def is_graph_skeleton(graph: nx.MultiDiGraph) -> bool:
    """True if graph looks like a TVE graph data skeleton (no rich attributes).

    A skeleton has numeric-string or auto-generated IDs
    and label == type (or label == id) on most nodes.
    """
    if graph.number_of_nodes() == 0:
        return False

    skeleton_nodes = 0
    for _, data in graph.nodes(data=True):
        node_id = str(data.get("id", ""))
        label = data.get("label", "")
        ntype = data.get("type", "")

        is_numeric_id = node_id.isdigit()
        label_matches_type = label == ntype
        label_matches_id = label == node_id

        if is_numeric_id and (label_matches_type or label_matches_id):
            skeleton_nodes += 1

    # If more than half the nodes look skeletal, it's a skeleton
    return skeleton_nodes > graph.number_of_nodes() / 2


def auto_label_nodes(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Assign unique display labels to skeleton nodes.

    Nodes with the same type get numbered: BusinessProcess_0,
    BusinessProcess_1, etc. Nodes with unique types keep the
    type as label without a suffix.

    Mutates and returns the same graph.
    """
    # Count how many nodes share each type
    type_counts: Counter[str] = Counter(
        data.get("type", "unknown") for _, data in graph.nodes(data=True)
    )

    # Track the next index per type
    type_index: dict[str, int] = {}

    for node_id, data in graph.nodes(data=True):
        ntype = data.get("type", "unknown")

        if type_counts[ntype] > 1:
            # Give ID names to same types
            idx = type_index.get(ntype, 0)
            type_index[ntype] = idx + 1
            data["label"] = f"{ntype}_{idx}"
        else:
            data["label"] = ntype

    return graph


def safe_alias(raw: str) -> str:
    """Create a PlantUML-safe alias from any string.

    Replaces non-alphanumeric chars with underscore,
    ensures it starts with a letter.
    """
    alias = "".join(c if c.isalnum() else "_" for c in str(raw))
    if not alias or not alias[0].isalpha():
        alias = f"N{alias}"
    return alias