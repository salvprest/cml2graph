import networkx as nx

from cml2graph.core.prompts import summarize_graph

from .utils.types import ELEMENT_LAYER, RELATIONSHIP_TYPES

# Derived enums
_LAYERS: list[str] = sorted(set(ELEMENT_LAYER.values()))
_ELEMENT_TYPES: list[str] = sorted(ELEMENT_LAYER.keys())
_RELATIONSHIP_TYPES: list[str] = sorted(RELATIONSHIP_TYPES)


#  Metadata for the filter tools
#  Keys must match the keys returned by plugin.get_filters()
FILTER_TOOLS: dict[str, dict] = {
    "by_layer": {
        "description": (
            "Filter the ArchiMate graph to keep only elements "
            "belonging to the specified layers. Removes non-matching "
            "nodes and their incident edges."
        ),
        "params": {
            "layers": {
                "description": "ArchiMate layers to keep.",
                "type": "array",
                "enum": _LAYERS,
            },
        },
    },
    "by_element_type": {
        "description": (
            "Keep only nodes whose ArchiMate element type matches "
            "one of the given values. Removes non-matching nodes "
            "and their incident edges."
        ),
        "params": {
            "types": {
                "description": "ArchiMate element types to keep.",
                "type": "array",
                "enum": _ELEMENT_TYPES,
            },
        },
    },
    "by_relationship_type": {
        "description": (
            "Keep all nodes but remove edges whose relationship type "
            "does not match any of the given values."
        ),
        "params": {
            "types": {
                "description": "ArchiMate relationship types to keep.",
                "type": "array",
                "enum": _RELATIONSHIP_TYPES,
            },
        },
    },
}


def _format_layer_elements() -> str:
    # Format the list of element types grouped by layer, for prompt inclusion.
    by_layer: dict[str, list[str]] = {}
    for elem, layer in sorted(ELEMENT_LAYER.items()):
        by_layer.setdefault(layer, []).append(elem)
    lines = []
    for layer in sorted(by_layer):
        lines.append(f"  {layer}: {', '.join(sorted(by_layer[layer]))}")
    return "\n".join(lines)


GENERAL_PROMPT: str = """\
You are analysing an ArchiMate enterprise-architecture model.
ArchiMate organises elements into layers and connects them with
typed relationships.

- Layers and Element Types:

{layer_elements}

- Relationship Types:

{relationship_types}

- This Model:

{graph_summary}

- Task:

    Describe:
    1. Which layers are represented and how heavily each is used.
    2. What element types appear and their architectural role.
    3. What relationship types connect elements; dominant patterns.
    4. Cross-layer dependencies (Business to Application to Technology).
    5. Overall architectural style and notable design decisions.
"""


def build_prompt_context(graph: nx.MultiDiGraph) -> dict[str, str]:
    return {
        "layer_elements": _format_layer_elements(),
        "relationship_types": ", ".join(_RELATIONSHIP_TYPES),
        "graph_summary": summarize_graph(graph),
    }
