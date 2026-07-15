from collections import Counter

import networkx as nx

from cml2graph.core.prompts import summarize_graph_stat_string

from .utils.types import (
    CLASS_STEREOTYPES,
    NON_SORTAL_STEREOTYPES,
    RELATION_STEREOTYPES,
    RELATIONSHIP_TYPES,
    SORTAL_STEREOTYPES,
    STEREOTYPE_CATEGORY,
)

_CLASS_STEREOTYPES: list[str] = sorted(CLASS_STEREOTYPES)
_RELATION_STEREOTYPES: list[str] = sorted(RELATION_STEREOTYPES)
_RELATIONSHIP_TYPES: list[str] = sorted(RELATIONSHIP_TYPES)
_CATEGORIES: list[str] = sorted(set(STEREOTYPE_CATEGORY.values()))
_NATURES: list[str] = [
    "abstract", "collective", "event", "functional-complex",
    "mode", "quality", "quantity", "relator", "situation", "type",
]


FILTER_TOOLS: dict[str, dict] = {
    "by_stereotype": {
        "description": (
            "Filter nodes by OntoUML stereotype. By default (exclude=False) "
            "keeps only matching nodes; set exclude=True to remove them instead. "
            "Incident edges are updated accordingly."
        ),
        "params": {
            "stereotypes": {
                "description": "OntoUML class stereotypes to select.",
                "type": "array",
                "enum": _CLASS_STEREOTYPES,
            },
            "exclude": {
                "description": "If true, remove the matching nodes instead of keeping them.",
                "type": "boolean",
            },
        },
    },
    "by_category": {
        "description": (
            "Filter nodes by ontological category. Categories group stereotypes: "
            "Substantial (kind, subkind, role…), Moment (relator, quality, mode), "
            "NonSortal (category, mixin…), Event, Situation. "
            "By default (exclude=False) keeps only matching nodes; set exclude=True to remove them."
        ),
        "params": {
            "categories": {
                "description": "Ontological categories to select.",
                "type": "array",
                "enum": _CATEGORIES,
            },
            "exclude": {
                "description": "If true, remove the matching nodes instead of keeping them.",
                "type": "boolean",
            },
        },
    },
    "by_relation": {
        "description": (
            "Filter edges by OntoUML relation stereotype. By default (exclude=False) "
            "keeps only matching edges; set exclude=True to remove them instead. "
            "All nodes are preserved."
        ),
        "params": {
            "types": {
                "description": "Relation stereotypes to select.",
                "type": "array",
                "enum": _RELATION_STEREOTYPES,
            },
            "exclude": {
                "description": "If true, remove the matching edges instead of keeping them.",
                "type": "boolean",
            },
        },
    },
    "by_generalization": {
        "description": (
            "Filter generalization edges. By default (exclude=False) removes all "
            "non-generalization edges; set exclude=True to remove generalization "
            "edges instead. All nodes are preserved."
        ),
        "params": {
            "exclude": {
                "description": "If true, remove generalization edges instead of keeping them.",
                "type": "boolean",
            },
        },
    },
    "by_ontological_nature": {
        "description": (
            "Filter nodes by ontological nature (restrictedTo). By default (exclude=False) "
            "keeps only nodes whose nature contains at least one of the requested values; "
            "set exclude=True to remove those nodes instead."
        ),
        "params": {
            "natures": {
                "description": "Ontological natures to select.",
                "type": "array",
                "enum": _NATURES,
            },
            "exclude": {
                "description": "If true, remove the matching nodes instead of keeping them.",
                "type": "boolean",
            },
        },
    },
    # "without_orphans": {
    #     "description": (
    #         "Remove nodes with degree zero. Typically used after "
    #         "another filter has removed edges, leaving isolated nodes."
    #     ),
    #     "params": {},
    # },
    # "exclude_node_types": {
    #     "description": "Remove nodes whose type matches any given value.",
    #     "params": {
    #         "types": {
    #             "description": "Node types (stereotypes) to remove.",
    #             "type": "array",
    #             "enum": _CLASS_STEREOTYPES,
    #         },
    #     },
    # },
    # "exclude_edge_types": {
    #     "description": "Remove edges whose type matches any given value.",
    #     "params": {
    #         "types": {
    #             "description": "Edge types to remove.",
    #             "type": "array",
    #             "enum": _RELATIONSHIP_TYPES,
    #         },
    #     },
    # },
    # "normalize_types": {
    #     "description": (
    #         "Replace specific stereotypes with generic labels "
    #         "('class', 'relation') for abstracted graph mining."
    #     ),
    #     "params": {
    #         "class_stereotypes": {
    #             "description": "Class stereotypes to normalise. Defaults to all.",
    #             "type": "array",
    #             "enum": _CLASS_STEREOTYPES,
    #             "required": False,
    #         },
    #         "relation_stereotypes": {
    #             "description": "Relation stereotypes to normalise. Defaults to all.",
    #             "type": "array",
    #             "enum": _RELATION_STEREOTYPES,
    #             "required": False,
    #         },
    #     },
    # },
}


MAX_VOCAB_NAMES: int = 80
def _collect_vocabulary(graph: nx.MultiDiGraph) -> str:
    """Compact list of node labels grouped by stereotype.

    Keeps at most *MAX_VOCAB_NAMES* names so the prompt stays
    manageable even for large models.
    """
    by_type: dict[str, list[str]] = {}
    for _, d in graph.nodes(data=True):
        label = d.get("label", "")
        stereotype = d.get("type", "unknown")
        if label and label != stereotype:
            by_type.setdefault(stereotype, []).append(label)

    lines: list[str] = []
    total = 0
    for st, names in sorted(by_type.items()):
        unique = sorted(set(names))
        remaining = MAX_VOCAB_NAMES - total
        if remaining <= 0:
            break
        batch = unique[:remaining]
        total += len(batch)
        suffix = f" (+{len(unique) - len(batch)} more)" if len(batch) < len(unique) else ""
        lines.append(f"  {st}: {', '.join(batch)}{suffix}")
    return "\n".join(lines) if lines else "  (no named nodes)"


def _format_stereotype_categories() -> str:
    by_cat: dict[str, list[str]] = {}
    for st, cat in sorted(STEREOTYPE_CATEGORY.items()):
        by_cat.setdefault(cat, []).append(st)
    return "\n".join(
        f"  {cat}: {', '.join(sorted(sts))}"
        for cat, sts in sorted(by_cat.items())
    )


def _summarize_categories(graph: nx.MultiDiGraph) -> str:
    """Count nodes by their stereotype category as found in the graph."""
    counts: Counter[str] = Counter(
        d.get("category", "") or "(none)"
        for _, d in graph.nodes(data=True)
    )
    if not counts:
        return "  (no data)"
    return "\n".join(
        f"  {cat}: {c}" for cat, c in counts.most_common()
    )


def _summarize_natures(graph: nx.MultiDiGraph) -> str:
    """Count occurrences of each nature value across all nodes."""
    counts: Counter[str] = Counter()
    for _, d in graph.nodes(data=True):
        nature_str = d.get("nature", "") or ""
        for n in nature_str.split(","):
            n = n.strip()
            if n:
                counts[n] += 1
    if not counts:
        return "  (no restrictedTo data)"
    return "\n".join(
        f"  {nat}: {c}" for nat, c in counts.most_common()
    )


def _summarize_stereotypes(graph: nx.MultiDiGraph) -> str:
    """Count nodes by stereotype, grouped into sortal and non-sortal."""
    counts: Counter[str] = Counter(
        d.get("stereotype", "unknown") for _, d in graph.nodes(data=True)
    )
    if not counts:
        return "  (no nodes)"

    sortal = [(s, counts[s]) for s in sorted(counts) if s in SORTAL_STEREOTYPES]
    non_sortal = [(s, counts[s]) for s in sorted(counts) if s in NON_SORTAL_STEREOTYPES]
    other = [(s, counts[s]) for s in sorted(counts)
             if s not in SORTAL_STEREOTYPES and s not in NON_SORTAL_STEREOTYPES]

    lines: list[str] = []
    if sortal:
        lines.append("  Sortal: " + ", ".join(f"{s} ({c})" for s, c in sortal))
    if non_sortal:
        lines.append("  Non-sortal: " + ", ".join(f"{s} ({c})" for s, c in non_sortal))
    if other:
        lines.append("  Other: " + ", ".join(f"{s} ({c})" for s, c in other))
    return "\n".join(lines)


def _summarize_relations(graph: nx.MultiDiGraph) -> str:
    """Count edges by relation stereotype (excluding generalization)."""
    counts: Counter[str] = Counter(
        d.get("type", "unknown")
        for _, _, d in graph.edges(data=True)
        if d.get("type") != "generalization"
    )
    if not counts:
        return "  (no relations)"
    return "\n".join(
        f"  {rel}: {c}" for rel, c in counts.most_common()
    )

def _summarize_generalizations(graph: nx.MultiDiGraph) -> str:
    """Summarize generalization edges and generalization sets from the graph."""
    gen_count = sum(
        1 for _, _, d in graph.edges(data=True)
        if d.get("type") == "generalization"
    )
    gs_list: list[dict] = graph.graph.get("generalization_sets", [])

    lines: list[str] = [f"  Generalization edges: {gen_count}"]

    if gs_list:
        lines.append(f"  Generalization sets: {len(gs_list)}")
        for gs in gs_list:
            name = gs.get("name") or gs.get("id", "unnamed")
            disjoint = gs.get("isDisjoint", False)
            complete = gs.get("isComplete", False)
            constraints: list[str] = []
            if disjoint:
                constraints.append("disjoint")
            if complete:
                constraints.append("complete")
            constraint_str = f" ({', '.join(constraints)})" if constraints else ""
            gen_count_in_set = len(gs.get("generalizations", []))
            lines.append(
                f"    {name}: {gen_count_in_set} generalizations{constraint_str}"
            )
    else:
        lines.append("  Generalization sets: 0")

    return "\n".join(lines)


GENERAL_PROMPT: str = """\
You are analysing an OntoUML conceptual model grounded in the
Unified Foundational Ontology (UFO).

- Class Stereotypes:
Sortal: {sortal_stereotypes}
Non-sortal: {non_sortal_stereotypes}
Stereotype distribution in this model:
{stereotype_distribution}

- Relations:
{relation_stereotypes}
Relation distribution in this model:
{relation_distribution}

- Generalizations:
{generalization_summary}

- Ontological Categories:
{stereotype_categories}
Ontological category distribution:
{category_distribution}

- Ontological Nature (restrictedTo):
Ontological nature distribution
{nature_distribution}

- This model graph summary:
{graph_summary}

- Domain Vocabulary:
{vocabulary}

- Filters:
{filters}

- Task:

    Describe:
    - Which stereotypes are used and statistics data.
    - Which relations appear and statistics data.
    - Which generalization sets appear and statistics data.
    - Which ontological categories are present and statistics data.
    - Which ontological natures (restrictedTo) appear and statistics data.
    - If not empty, use the vocabulary entries, without listing them, to infer the domain this model represents.
    - List the filters you can apply and their available targets for the given model.

"""


def build_prompt_context(graph: nx.MultiDiGraph) -> dict[str, str]:
    """Fill every placeholder in GENERAL_PROMPT."""
    return {
        "sortal_stereotypes": ", ".join(sorted(SORTAL_STEREOTYPES)),
        "non_sortal_stereotypes": ", ".join(sorted(NON_SORTAL_STEREOTYPES)),
        "relation_stereotypes": ", ".join(sorted(RELATION_STEREOTYPES)),
        "stereotype_distribution": _summarize_stereotypes(graph),
        "relation_distribution": _summarize_relations(graph),
        "stereotype_categories": _format_stereotype_categories(),
        "graph_summary": summarize_graph_stat_string(graph),
        "category_distribution": _summarize_categories(graph),
        "nature_distribution": _summarize_natures(graph),
        "generalization_summary": _summarize_generalizations(graph),
        "vocabulary": _collect_vocabulary(graph),
        "filters": ", ".join(list(FILTER_TOOLS.keys())),
    }
