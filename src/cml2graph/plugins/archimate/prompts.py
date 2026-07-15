from collections import Counter

import networkx as nx

from cml2graph.core.prompts import summarize_graph_stat_string

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
            "Filter the ArchiMate graph by layer. By default (exclude=False) "
            "keeps only nodes in the specified layers; set exclude=True to "
            "remove those nodes instead. Incident edges are updated accordingly."
        ),
        "params": {
            "layers": {
                "description": "ArchiMate layers to select.",
                "type": "array",
                "enum": _LAYERS,
            },
            "exclude": {
                "description": "If true, remove the matching nodes instead of keeping them.",
                "type": "boolean",
            },
        },
    },
    "by_element_type": {
        "description": (
            "Filter nodes by ArchiMate element type. By default (exclude=False) "
            "keeps only matching nodes; set exclude=True to remove them instead. "
            "Incident edges are updated accordingly."
        ),
        "params": {
            "types": {
                "description": "ArchiMate element types to select.",
                "type": "array",
                "enum": _ELEMENT_TYPES,
            },
            "exclude": {
                "description": "If true, remove the matching nodes instead of keeping them.",
                "type": "boolean",
            },
        },
    },
    "by_relationship_type": {
        "description": (
            "Filter edges by ArchiMate relationship type. By default (exclude=False) "
            "keeps only matching edges; set exclude=True to remove them instead. "
            "All nodes are preserved."
        ),
        "params": {
            "types": {
                "description": "ArchiMate relationship types to select.",
                "type": "array",
                "enum": _RELATIONSHIP_TYPES,
            },
            "exclude": {
                "description": "If true, remove the matching edges instead of keeping them.",
                "type": "boolean",
            },
        },
    },
}


MAX_VOCAB_NAMES: int = 80
def _collect_vocabulary(graph: nx.MultiDiGraph) -> str:
    """Compact list of element names grouped by type.

    Keeps at most *MAX_VOCAB_NAMES* names so the prompt stays
    manageable even for large models.
    """
    by_type: dict[str, list[str]] = {}
    for _, d in graph.nodes(data=True):
        label = d.get("label", "")
        etype = d.get("type", "unknown")
        if label and label != etype:
            by_type.setdefault(etype, []).append(label)

    lines: list[str] = []
    total = 0
    for etype, names in sorted(by_type.items()):
        unique = sorted(set(names))
        remaining = MAX_VOCAB_NAMES - total
        if remaining <= 0:
            break
        batch = unique[:remaining]
        total += len(batch)
        suffix = f" (+{len(unique) - len(batch)} more)" if len(batch) < len(unique) else ""
        lines.append(f"  {etype}: {', '.join(batch)}{suffix}")
    return "\n".join(lines) if lines else "  (no named elements)"


def _format_layer_elements() -> str:
    # Format the list of element types grouped by layer, for prompt inclusion.
    by_layer: dict[str, list[str]] = {}
    for elem, layer in sorted(ELEMENT_LAYER.items()):
        by_layer.setdefault(layer, []).append(elem)
    lines = []
    for layer in sorted(by_layer):
        lines.append(f"  {layer}: {', '.join(sorted(by_layer[layer]))}")
    return "\n".join(lines)


def _summarize_layers(graph: nx.MultiDiGraph) -> str:
    """Count nodes by their ArchiMate layer."""
    counts: Counter[str] = Counter(
        d.get("layer", "(none)") or "(none)"
        for _, d in graph.nodes(data=True)
    )
    if not counts:
        return "  (no nodes)"
    return "\n".join(
        f"  {layer}: {c}" for layer, c in counts.most_common()
    )


def _summarize_element_types(graph: nx.MultiDiGraph) -> str:
    """Count nodes by their ArchiMate element type."""
    counts: Counter[str] = Counter(
        d.get("type", "unknown") for _, d in graph.nodes(data=True)
    )
    if not counts:
        return "  (no nodes)"
    return "\n".join(
        f"  {etype}: {c}" for etype, c in counts.most_common()
    )


def _summarize_relationships(graph: nx.MultiDiGraph) -> str:
    """Count edges by their ArchiMate relationship type."""
    counts: Counter[str] = Counter(
        d.get("type", "unknown") for _, _, d in graph.edges(data=True)
    )
    if not counts:
        return "  (no relationships)"
    return "\n".join(
        f"  {rtype}: {c}" for rtype, c in counts.most_common()
    )


GENERAL_PROMPT: str = """\
You are analysing an ArchiMate enterprise-architecture model.
ArchiMate organises elements into layers and connects them with
typed relationships.

You have these information available:
- Layers:
{layer_elements}
Layer distribution in this model:
{layer_distribution}

- Element Types:
{element_types}
Element type distribution in this model:
{element_type_distribution}

- Relationship Types:
{relationship_types}
Relationship distribution in this model:
{relationship_distribution}

- This model graph summary:
{graph_summary}

- Domain Vocabulary (element names found in the model):
{vocabulary}

- Filters:
{filters}

- Task:

    Describe:
    - Which layers are represented and statistics data.
    - What element types appear and statistics data.
    - What relationship types appear; and statistics data.
    - If not empty, use the vocabulary entries, without listing them, to infer the domain this model represents.
    - List the filters you can apply and their available targets for the given model.
"""


def build_prompt_context(graph: nx.MultiDiGraph) -> dict[str, str]:
    return {
        "layer_elements": _format_layer_elements(),
        "element_types": ", ".join(_ELEMENT_TYPES),
        "relationship_types": ", ".join(_RELATIONSHIP_TYPES),
        "graph_summary": summarize_graph_stat_string(graph),
        "layer_distribution": _summarize_layers(graph),
        "element_type_distribution": _summarize_element_types(graph),
        "relationship_distribution": _summarize_relationships(graph),
        "vocabulary": _collect_vocabulary(graph),
        "filters": ", ".join(list(FILTER_TOOLS.keys())),
    }
