import networkx as nx

from cml2graph.core.prompts import summarize_graph

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
            "Keep only nodes whose OntoUML stereotype matches one "
            "of the given values. Non-matching nodes and their "
            "incident edges are removed."
        ),
        "params": {
            "stereotypes": {
                "description": "OntoUML class stereotypes to keep.",
                "enum": _CLASS_STEREOTYPES,
            },
        },
    },
    "by_category": {
        "description": (
            "Keep only nodes in the given semantic categories. "
            "Categories group stereotypes: Substantial (kind, subkind, "
            "role…), Moment (relator, quality, mode), NonSortal "
            "(category, mixin…), Event, Situation."
        ),
        "params": {
            "categories": {
                "description": "Semantic categories to keep.",
                "enum": _CATEGORIES,
            },
        },
    },
    "by_relationship_type": {
        "description": (
            "Keep all nodes but remove edges whose type does not "
            "match one of the given relationship types."
        ),
        "params": {
            "types": {
                "description": "Relationship types to keep.",
                "enum": _RELATIONSHIP_TYPES,
            },
        },
    },
    "by_nature": {
        "description": (
            "Keep only nodes whose ontological nature (restrictedTo) "
            "contains at least one of the requested values."
        ),
        "params": {
            "natures": {
                "description": "Ontological natures to keep.",
                "enum": _NATURES,
            },
        },
    },
    "without_orphans": {
        "description": (
            "Remove nodes with degree zero. Typically used after "
            "another filter has removed edges, leaving isolated nodes."
        ),
        "params": {},
    },
    "exclude_node_types": {
        "description": "Remove nodes whose type matches any given value.",
        "params": {
            "types": {
                "description": "Node types (stereotypes) to remove.",
                "enum": _CLASS_STEREOTYPES,
            },
        },
    },
    "exclude_edge_types": {
        "description": "Remove edges whose type matches any given value.",
        "params": {
            "types": {
                "description": "Edge types to remove.",
                "enum": _RELATIONSHIP_TYPES,
            },
        },
    },
    "normalize_types": {
        "description": (
            "Replace specific stereotypes with generic labels "
            "('class', 'relation') for abstracted graph mining."
        ),
        "params": {
            "class_stereotypes": {
                "description": "Class stereotypes to normalise. Defaults to all.",
                "enum": _CLASS_STEREOTYPES,
                "required": False,
            },
            "relation_stereotypes": {
                "description": "Relation stereotypes to normalise. Defaults to all.",
                "enum": _RELATION_STEREOTYPES,
                "required": False,
            },
        },
    },
}


def _format_categories() -> str:
    by_cat: dict[str, list[str]] = {}
    for st, cat in sorted(STEREOTYPE_CATEGORY.items()):
        by_cat.setdefault(cat, []).append(st)
    return "\n".join(
        f"  {cat}: {', '.join(sorted(sts))}"
        for cat, sts in sorted(by_cat.items())
    )


GENERAL_PROMPT: str = """\
You are analysing an OntoUML conceptual model grounded in the
Unified Foundational Ontology (UFO).

- Class Stereotypes:

Sortal: {sortal_stereotypes}
Non-sortal: {non_sortal_stereotypes}

- Relationship Types:

Relations: {relation_stereotypes}
Structural: generalization, restrictedTo

- Semantic Categories:

{categories}

- This Model:

{graph_summary}

- Task:

    Describe:
    1. The domain this model represents.
    2. Which stereotypes are used and their ontological meaning.
    3. Which relationships connect classes; multiplicities if visible.
    4. Generalisation hierarchies and their constraints.
    5. Overall ontological structure and UFO patterns.
"""


def build_prompt_context(graph: nx.MultiDiGraph) -> dict[str, str]:
    """Fill every placeholder in GENERAL_PROMPT."""
    return {
        "sortal_stereotypes": ", ".join(sorted(SORTAL_STEREOTYPES)),
        "non_sortal_stereotypes": ", ".join(sorted(NON_SORTAL_STEREOTYPES)),
        "relation_stereotypes": ", ".join(sorted(RELATION_STEREOTYPES)),
        "categories": _format_categories(),
        "graph_summary": summarize_graph(graph),
    }
