import json
from collections import defaultdict
from typing import Any

import networkx as nx

from .utils.types import RELATION_STEREOTYPES, PART_WHOLE_STEREOTYPES

_RELATION_STEREOTYPES_LOWER: frozenset[str] = frozenset(
    s.lower() for s in RELATION_STEREOTYPES
)
_PART_WHOLE_STEREOTYPES_LOWER: frozenset[str] = frozenset(
    s.lower() for s in PART_WHOLE_STEREOTYPES
)

_ONTOUML_SKINPARAMS = """\
' OntoUML formatting
skinparam roundcorner 10
skinparam classBorderColor #333333
skinparam classFontName Arial
skinparam shadowing false
hide circle
hide members

' Layout tuning
skinparam linetype ortho
skinparam nodesep 100
skinparam ranksep 80
skinparam padding 4

' OntoUML Smart Paint Color Palette
skinparam class {
    BackgroundColor<<kind>> #FFB6C1
    BackgroundColor<<subkind>> #FFB6C1
    BackgroundColor<<collective>> #FFB6C1
    BackgroundColor<<quantity>> #FFB6C1
    BackgroundColor<<role>> #FFFFCC
    BackgroundColor<<phase>> #FFFFCC
    BackgroundColor<<historicalRole>> #FFFFCC
    BackgroundColor<<category>> #E0FFFF
    BackgroundColor<<mixin>> #E0FFFF
    BackgroundColor<<roleMixin>> #E0FFFF
    BackgroundColor<<phaseMixin>> #E0FFFF
    BackgroundColor<<historicalRoleMixin>> #E0FFFF
    BackgroundColor<<abstract>> #E0FFFF
    BackgroundColor<<relator>> #CCFFCC
    BackgroundColor<<mode>> #E6E6FA
    BackgroundColor<<quality>> #E6E6FA
    BackgroundColor<<event>> #F08080
    BackgroundColor<<situation>> #F08080
    BackgroundColor<<datatype>> #FFDAB9
    BackgroundColor<<enumeration>> #FFDAB9
    BackgroundColor<<type>> #FFDAB9
}
"""

class _LayoutInfo:
    """Pre-computed layout hints derived from graph topology."""

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        # Build a directed tree: specific -> general (child -> parent)
        self.gen_tree: nx.DiGraph = nx.DiGraph()
        for u, v, d in graph.edges(data=True):
            if d.get("type", "").lower() == "generalization":
                self.gen_tree.add_edge(u, v)

        # Assign depth: roots (nodes with no outgoing gen-tree edge) = 0
        self.depth: dict[Any, int] = {}
        if self.gen_tree.number_of_nodes() > 0:
            roots = [n for n in self.gen_tree.nodes()
                     if self.gen_tree.out_degree(n) == 0]
            rev = self.gen_tree.reverse()
            for root in roots:
                if root not in self.depth:
                    self.depth[root] = 0
                for edge_u, edge_v in nx.bfs_edges(rev, root):
                    self.depth[edge_v] = self.depth[edge_u] + 1

        for n in graph.nodes():
            if n not in self.depth:
                self.depth[n] = 0

        # Map general -> [specifics] (parent -> children)
        self._children_of: dict[Any, list[Any]] = defaultdict(list)
        for u, v, d in graph.edges(data=True):
            if d.get("type", "").lower() == "generalization":
                self._children_of[v].append(u)

    def siblings_of(self, parent: Any) -> list[Any]:
        return self._children_of.get(parent, [])

    def is_deeper(self, a: Any, b: Any) -> bool:
        return self.depth.get(a, 0) > self.depth.get(b, 0)

    def same_level(self, a: Any, b: Any) -> bool:
        return self.depth.get(a, 0) == self.depth.get(b, 0)


# Direction helpers
def _gen_direction(layout: _LayoutInfo, specific: Any, general: Any) -> str:
    """Generalization always points upward (specific -> general)."""
    return "up"


def _assoc_direction(
    layout: _LayoutInfo, src: Any, tgt: Any, is_self: bool
) -> str:
    """
    Self-loops go right. Same-level relations use no forced direction so
    Graphviz can minimise crossings. Cross-level relations go up or down.
    """
    if is_self:
        return "right"
    if layout.same_level(src, tgt):
        return ""
    if layout.is_deeper(src, tgt):
        return "up"
    return "down"


def _partwhole_direction(
    layout: _LayoutInfo, part: Any, whole: Any, is_self: bool
) -> str:
    """
    The arrow is emitted as ``{whole} *-{dir}- {part}``.
    Whole is typically above part, so ``down`` places part below whole.
    Same-level composites use no forced direction.
    """
    if is_self:
        return "right"
    if layout.same_level(part, whole):
        return ""
    return "down"


# Arrow builder
def _make_arrow(direction: str, style: str) -> str:
    """
    Build a PlantUML arrow string.

    When ``direction`` is empty, produce a natural arrow and let Graphviz
    choose the best placement (no forced axis).

    style ``gen`` -> ``-dir-|>``  / ``--|>``
    style ``partwhole`` -> ``*-dir-``   / ``*--``
    style ``assoc`` -> ``-dir->``   / ``-->``
    style ``dashed`` -> ``.[#888888].dir.>`` / ``.[#888888].>``
    """
    if not direction:
        if style == "gen":
            return "--|>"
        if style == "partwhole":
            return "*--"
        if style == "dashed":
            return ".[#888888].>"
        return "-->"

    if style == "gen":
        return f"-{direction}-|>"
    if style == "partwhole":
        return f"*-{direction}-"
    if style == "dashed":
        return f".[#888888].{direction}.>"
    return f"-{direction}->"


# Node info helper
def _compute_node_info(
    graph: nx.MultiDiGraph,
) -> dict[Any, tuple[str, str, str]]:
    """Return ``{node_id: (alias, display_name, stereotype)}`` for every node."""
    class_counter: dict[str, int] = {}
    info: dict[Any, tuple[str, str, str]] = {}
    for nid, d in graph.nodes(data=True):
        alias = _safe_alias(nid)
        stereotype = d.get("stereotype") or d.get("type", "class")
        name = d.get("label", stereotype)
        if name in (stereotype, str(nid)):
            idx = class_counter.get(stereotype, 0)
            class_counter[stereotype] = idx + 1
            display = f"{stereotype}_{idx}"
        else:
            display = name
        info[nid] = (alias, display, stereotype)
    return info


class OntoUMLPlantUMLRenderer:

    @property
    def format_name(self) -> str:
        return "plantuml"

    def render(self, graph: nx.MultiDiGraph) -> str:
        layout = _LayoutInfo(graph)
        node_info = _compute_node_info(graph)
        title = graph.graph.get("model_id", "OntoUML")

        lines: list[str] = [
            "@startuml",
            f"title {title}",
            "",
            _ONTOUML_SKINPARAMS,
        ]

        # Emit sibling groups inside `together {}` so PlantUML keeps them
        # horizontally adjacent; track which nodes were declared there.
        grouped = self._render_sibling_groups(node_info, layout, lines)

        # Remaining (ungrouped) nodes
        for nid in graph.nodes():
            if nid not in grouped:
                alias, display, stereotype = node_info[nid]
                lines.append(f'class "{display}" as {alias} <<{stereotype}>>')

        lines.append("")
        self._render_edges(graph, layout, lines)
        lines.append("")
        lines.append("@enduml")
        return "\n".join(lines)

    # Sibling grouping
    @staticmethod
    def _render_sibling_groups(
        node_info: dict[Any, tuple[str, str, str]],
        layout: _LayoutInfo,
        lines: list[str],
    ) -> set[Any]:
        """
        Emit ``together {}`` blocks for sibling subclasses (children of the
        same parent) to keep them horizontally adjacent in the layout.

        Full class declarations are placed *inside* the block so PlantUML
        picks up stereotypes and display names correctly (no double-declare).

        Returns the set of node IDs that were emitted inside together blocks.
        """
        grouped: set[Any] = set()
        seen_groups: set[frozenset] = set()

        for parent, children in layout._children_of.items():
            if len(children) < 2:
                continue
            group_key = frozenset(children)
            if group_key in seen_groups:
                continue
            seen_groups.add(group_key)

            lines.append("together {")
            for child in children:
                alias, display, stereotype = node_info[child]
                lines.append(f'  class "{display}" as {alias} <<{stereotype}>>')
                grouped.add(child)
            lines.append("}")
            lines.append("")

        return grouped

    # Edges
    @staticmethod
    def _render_edges(
        graph: nx.MultiDiGraph,
        layout: _LayoutInfo,
        lines: list[str],
    ) -> None:
        for u, v, _k, d in graph.edges(keys=True, data=True):
            src = _safe_alias(u)
            tgt = _safe_alias(v)
            etype = d.get("type", "")
            etype_lower = etype.lower()
            is_self = src == tgt

            if etype_lower == "generalization":
                direction = _gen_direction(layout, u, v)
                arrow = _make_arrow(direction, "gen")
                meta = _gen_meta_from_lists(
                    d.get("genset_names", []),
                    d.get("genset_is_disjoint", []),
                    d.get("genset_is_complete", []),
                )
                label = f" :{meta}" if meta else ""
                lines.append(f"{src} {arrow} {tgt}{label}")

            elif etype_lower in _PART_WHOLE_STEREOTYPES_LOWER:
                direction = _partwhole_direction(layout, u, v, is_self)
                arrow = _make_arrow(direction, "partwhole")
                left = f'"{d.get("cardinality_target", "")}" ' if d.get("cardinality_target") else ""
                right = f' "{d.get("cardinality_source", "")}"' if d.get("cardinality_source") else ""
                lines.append(
                    f"{tgt} {left}{arrow}{right} {src} : \u00AB{etype}\u00BB"
                )

            elif etype_lower in _RELATION_STEREOTYPES_LOWER:
                direction = _assoc_direction(layout, u, v, is_self)
                arrow = _make_arrow(direction, "assoc")
                left = f'"{d.get("cardinality_source", "")}" ' if d.get("cardinality_source") else ""
                right = f' "{d.get("cardinality_target", "")}"' if d.get("cardinality_target") else ""
                label = f" : \u00AB{etype}\u00BB" if etype_lower != "relation" else ""
                lines.append(f"{src} {left}{arrow}{right} {tgt}{label}")

            elif etype_lower == "restrictedto":
                direction = _assoc_direction(layout, u, v, is_self)
                arrow = _make_arrow(direction, "dashed")
                lines.append(f"{src} {arrow} {tgt} : restrictedTo")

            else:
                direction = _assoc_direction(layout, u, v, is_self)
                arrow = _make_arrow(direction, "assoc")
                left = f'"{d.get("cardinality_source", "")}" ' if d.get("cardinality_source") else ""
                right = f' "{d.get("cardinality_target", "")}"' if d.get("cardinality_target") else ""
                label = f" : {etype}" if etype else ""
                lines.append(f"{src} {left}{arrow}{right} {tgt}{label}")


# Helpers

def _safe_alias(node_id: Any) -> str:
    """PlantUML-safe alias: replace non-alnum with ``_``, prefix with ``N``."""
    s = str(node_id)
    cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in s)
    return f"N{cleaned}" if cleaned else "Nnode"


def _gen_meta_from_lists(
    names: list[str],
    disjoint_flags: list[bool],
    complete_flags: list[bool],
) -> str:
    """
    Build annotation from all gensets this generalization belongs to.
    Example: ``" PersonTypes {disjoint} | LivingThings {complete}"``
    """
    if not names and not disjoint_flags and not complete_flags:
        return ""
    count = max(len(names), len(disjoint_flags), len(complete_flags))
    segments: list[str] = []
    for i in range(count):
        parts: list[str] = []
        if i < len(names) and names[i]:
            parts.append(names[i])
        if i < len(disjoint_flags) and disjoint_flags[i]:
            parts.append("{disjoint}")
        if i < len(complete_flags) and complete_flags[i]:
            parts.append("{complete}")
        if parts:
            segments.append(" ".join(parts))
    return " " + " | ".join(segments) if segments else ""


# JSON render ==========================================================

class OntoUMLJsonRenderer:

    @property
    def format_name(self) -> str:
        return "json"

    def render(self, graph: nx.MultiDiGraph) -> str:
        model: dict[str, Any] = {
            "type": "Package",
            "id": graph.graph.get("model_id", "model"),
            "name": graph.graph.get("model_id", "model"),
            "contents": [],
        }

        # classes
        for nid, d in graph.nodes(data=True):
            nature_raw = d.get("nature", "")
            restricted = [r for r in nature_raw.split(",") if r]

            cls: dict[str, Any] = {
                "type": "Class",
                "id": d.get("id", nid),
                "name": d.get("label", ""),
                "stereotype": d.get("stereotype") or d.get("type", "class"),
            }
            if restricted:
                cls["restrictedTo"] = restricted
            model["contents"].append(cls)

        # edges
        for u, v, k, d in graph.edges(keys=True, data=True):
            etype = d.get("type", "")

            if etype.lower() == "generalization":
                gen: dict[str, Any] = {
                    "type": "Generalization",
                    "id": d.get("id", k),
                    "general": {"id": v},
                    "specific": {"id": u},
                }
                model["contents"].append(gen)
            else:
                rel: dict[str, Any] = {
                    "type": "Relation",
                    "id": d.get("id", k),
                    "name": d.get("name", ""),
                    "stereotype": etype,
                    "properties": [
                        {
                            "propertyType": {"id": u},
                            "cardinality": d.get("cardinality_source", ""),
                        },
                        {
                            "propertyType": {"id": v},
                            "cardinality": d.get("cardinality_target", ""),
                        },
                    ],
                }
                model["contents"].append(rel)

        # generalization sets
        gs_meta = graph.graph.get("generalization_sets")
        if gs_meta:
            for gs in gs_meta:
                gs_elem: dict[str, Any] = {
                    "type": "GeneralizationSet",
                    "id": gs["id"],
                    "name": gs.get("name", ""),
                    "isDisjoint": gs.get("isDisjoint", False),
                    "isComplete": gs.get("isComplete", False),
                    "generalizations": [
                        {"id": gid}
                        for gid in gs.get("generalizations", [])
                    ],
                }
                model["contents"].append(gs_elem)
        else:
            # Reconstruct from edge attributes (list-based)
            gs_groups: dict[str, dict[str, Any]] = {}
            for u, v, k, d in graph.edges(keys=True, data=True):
                if d.get("type", "").lower() != "generalization":
                    continue
                genset_ids = d.get("genset_ids", [])
                genset_names = d.get("genset_names", [])
                disjoint_flags = d.get("genset_is_disjoint", [])
                complete_flags = d.get("genset_is_complete", [])
                edge_id = d.get("id", k)

                for i, gsid in enumerate(genset_ids):
                    if not gsid:
                        continue
                    if gsid not in gs_groups:
                        gs_groups[gsid] = {
                            "type": "GeneralizationSet",
                            "id": gsid,
                            "name": genset_names[i] if i < len(genset_names) else "",
                            "isDisjoint": disjoint_flags[i] if i < len(disjoint_flags) else False,
                            "isComplete": complete_flags[i] if i < len(complete_flags) else False,
                            "generalizations": [],
                        }
                    gs_groups[gsid]["generalizations"].append({"id": edge_id})
            model["contents"].extend(gs_groups.values())

        return json.dumps(model, indent=2, ensure_ascii=False)