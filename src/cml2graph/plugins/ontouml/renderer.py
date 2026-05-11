import json
from collections import defaultdict
from typing import Any

import networkx as nx

from .utils.types import RELATION_STEREOTYPES, PART_WHOLE_STEREOTYPES, AggregationKind
from .utils.colors import get_color_for_class

_RELATION_STEREOTYPES_LOWER: frozenset[str] = frozenset(
    s.lower() for s in RELATION_STEREOTYPES
)
_PART_WHOLE_STEREOTYPES_LOWER: frozenset[str] = frozenset(
    s.lower() for s in PART_WHOLE_STEREOTYPES
)

# Hollow diamond, separable parthood (memberOf only).
_HOLLOW_DIAMOND_STEREOTYPES: frozenset[str] = frozenset({
    "memberof",
})

# Filled diamond, inseparable parthood.
# subCollectionOf and participational are composite (filled), not shared.
_FILLED_DIAMOND_STEREOTYPES: frozenset[str] = frozenset({
    "componentof",
    "subcollectionof",
    "subquantityof",
    "participational",
})

# Dashed line + open arrow: derivation only.
# derivation connects a material relation to a relator class.
# instantiation is a regular navigable association, not dashed.
_DASHED_STEREOTYPES_LOWER: frozenset[str] = frozenset({
    "derivation",
})

_ONTOUML_SKINPARAMS = """\
<style>
classDiagram {
  class {
    FontName Arial
    LineColor #333333
    RoundCorner 10
    Padding 4
    Shadowing 0
  }
}
</style>

hide circle
hide members

' Layout tuning (no CSS equivalent yet)
skinparam linetype ortho
skinparam nodesep 100
skinparam ranksep 80
"""

# Ontological tier per stereotype, used as a fallback depth when a node
# is not reachable from the generalization tree.
#
# Tier 0 — abstract / cross-cutting non-sortals (most "general" visually)
# Tier 1 — ultimate sortals: identity providers (kind, collective, …)
# Tier 2 — moment types: relator, quality, mode
# Tier 3 — rigid specialisations: subkind
# Tier 4 — anti-rigid specialisations: role, phase, historicalRole
# Tier 5 — perdurants and abstracts: event, situation, type, datatype, …
#
# Non-sortals (category, mixin, …) stay at tier 0 because they span
# multiple identity hierarchies and the orthogonal layout places them
# horizontally alongside kind hierarchies.
_STEREOTYPE_TIER: dict[str, int] = {
    # Non-sortals (tier 0)
    "category": 0, "mixin": 0, "rolemixin": 0, "phasemixin": 0,
    "historicalrolemixin": 0, "abstract": 0,
    # Ultimate sortals (tier 1)
    "kind": 1, "collective": 1, "quantity": 1,
    # Moment types (tier 2)
    "relator": 2, "quality": 2, "mode": 2,
    # Rigid specialisations (tier 3)
    "subkind": 3,
    # Anti-rigid specialisations (tier 4)
    "role": 4, "phase": 4, "historicalrole": 4,
    # Perdurants / higher-order / datatypes (tier 5)
    "event": 5, "situation": 5, "type": 5,
    "enumeration": 5, "datatype": 5,
}


class _LayoutInfo:
    """Pre-computed layout hints derived from graph topology.

    Depth assignment (larger depth = visually lower = further down the page):

    Pass 1 — view coordinates (preferred):
        For every node that has view data, depth = view_y + view_height/2
        (vertical centre of the box in diagram pixels).  All depths are then
        normalised by subtracting the minimum, so the topmost node has depth 0
        and all others are relative to it.

    Pass 2 — fallback for nodes without view data:
        depth = _STEREOTYPE_TIER * _TIER_SCALE, where _TIER_SCALE places
        tier values in roughly the same pixel-range as the view-based depths
        (default 100 px per tier step).

    The generalization tree is still built for two purposes:
      - sibling grouping (``_children_of``)
      - direction hints (``_gen_direction``)
    …but it no longer drives depth: actual coordinates are more accurate.

    ``same_level`` uses a pixel tolerance (``_SAME_LEVEL_TOLERANCE``) so that
    boxes whose vertical centres differ by a few pixels still compare as equal.
    """

    _TIER_SCALE = 100        # pixels per stereotype tier step
    _SAME_LEVEL_TOLERANCE = 25  # px — half a typical 40px box height

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        # Pass 1: collect view-based depths (vertical centre of each box).
        raw: dict[Any, int] = {}
        for n, d in graph.nodes(data=True):
            vy = d.get("view_y")
            if vy is not None:
                vh = d.get("view_height") or 0
                raw[n] = int(vy) + int(vh) // 2

        # Normalise so the topmost node (smallest y) has depth 0.
        min_y = min(raw.values(), default=0)
        self.depth: dict[Any, int] = {n: v - min_y for n, v in raw.items()}

        # Pass 2: fallback for nodes with no view data.
        for n, d in graph.nodes(data=True):
            if n not in self.depth:
                stereotype = (d.get("stereotype") or d.get("type", "")).lower()
                tier = _STEREOTYPE_TIER.get(stereotype, 3)
                self.depth[n] = tier * self._TIER_SCALE

        # Build generalization tree (specific → general) for sibling groups
        # and direction hints.
        self.gen_tree: nx.DiGraph = nx.DiGraph()
        for u, v, d in graph.edges(data=True):
            if d.get("type", "").lower() == "generalization":
                self.gen_tree.add_edge(u, v)

        # Map general → [specifics] (parent → children).
        self._children_of: dict[Any, list[Any]] = defaultdict(list)
        for u, v, d in graph.edges(data=True):
            if d.get("type", "").lower() == "generalization":
                self._children_of[v].append(u)

    def siblings_of(self, parent: Any) -> list[Any]:
        return self._children_of.get(parent, [])

    def is_deeper(self, a: Any, b: Any) -> bool:
        return self.depth.get(a, 0) > self.depth.get(b, 0)

    def same_level(self, a: Any, b: Any) -> bool:
        return abs(self.depth.get(a, 0) - self.depth.get(b, 0)) <= self._SAME_LEVEL_TOLERANCE


# Direction helpers
def _gen_direction(layout: _LayoutInfo, specific: Any, general: Any) -> str:
    """
    Direction hint for a generalization arrow (specific -> general).

    Uses actual view coordinates when available:
    - specific deeper than general (standard case: general above specific) → "up"
    - general deeper than specific (unusual: general below specific) → "down"
    - same level → no hint (let Graphviz decide)
    """
    if layout.same_level(specific, general):
        return ""
    if layout.is_deeper(specific, general):
        return "up"
    return "down"


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

    Styles
    ------
    ``gen``         -> solid line + hollow triangle  (--|>)
    ``composition`` -> solid line + filled diamond   (*--)
    ``aggregation`` -> solid line + hollow diamond   (o--)
    ``assoc``       -> navigable arrow               (-->)
                       Target end is navigable for all non-mereology
                       stereotypes; mereology uses unspecified navigability.
    ``dashed``      -> dashed line + open arrow      (.[#888888].>)
    """
    if not direction:
        if style == "gen":
            return "--|>"
        if style == "composition":
            return "*--"
        if style == "aggregation":
            return "o--"
        if style == "dashed":
            return ".[#888888].>"
        # assoc: navigable arrow
        return "-->"

    if style == "gen":
        return f"-{direction}-|>"
    if style == "composition":
        return f"*-{direction}-"
    if style == "aggregation":
        return f"o-{direction}-"
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
        grouped = self._render_sibling_groups(graph, node_info, layout, lines)

        # Remaining (ungrouped) nodes — declare in top-to-bottom depth order
        # so that Graphviz declaration order nudges the layout to match the
        # original diagram's vertical arrangement.
        ungrouped = [
            (nid, data)
            for nid, data in graph.nodes(data=True)
            if nid not in grouped
        ]
        ungrouped.sort(key=lambda nd: layout.depth.get(nd[0], 0))
        for nid, node_data in ungrouped:
            alias, display, stereotype = node_info[nid]
            color = get_color_for_class(stereotype, node_data.get("nature", ""))
            lines.append(f'class "{display}" as {alias} <<{stereotype}>> {color}')

        lines.append("")
        self._render_edges(graph, layout, lines)
        lines.append("")
        lines.append("@enduml")
        return "\n".join(lines)

    # Sibling grouping
    @staticmethod
    def _render_sibling_groups(
        graph: nx.MultiDiGraph,
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

        # Collect unique sibling groups first, then sort them top-to-bottom.
        pending: list[tuple[int, list[Any]]] = []
        for parent, children in layout._children_of.items():
            if len(children) < 2:
                continue
            group_key = frozenset(children)
            if group_key in seen_groups:
                continue
            seen_groups.add(group_key)
            min_depth = min(layout.depth.get(c, 0) for c in children)
            pending.append((min_depth, children))

        pending.sort(key=lambda t: t[0])

        for _, children in pending:
            lines.append("together {")
            for child in children:
                alias, display, stereotype = node_info[child]
                color = get_color_for_class(stereotype, graph.nodes[child].get("nature", ""))
                lines.append(f'  class "{display}" as {alias} <<{stereotype}>> {color}')
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
                # Choose diamond type: hollow for memberOf/subCollectionOf,
                # filled for componentOf/subQuantityOf
                if etype_lower in _HOLLOW_DIAMOND_STEREOTYPES:
                    arrow = _make_arrow(direction, "aggregation")
                else:
                    arrow = _make_arrow(direction, "composition")
                left = f'"{d.get("cardinality_target", "")}" ' if d.get("cardinality_target") else ""
                right = f' "{d.get("cardinality_source", "")}"' if d.get("cardinality_source") else ""
                lines.append(
                    f"{tgt} {left}{arrow}{right} {src} : \u00AB{etype}\u00BB"
                )

            elif d.get("aggregation_kind", AggregationKind.NONE) in (AggregationKind.COMPOSITE, AggregationKind.SHARED):
                # Relation with no mereology stereotype but explicit aggregationKind
                # from the JSON property ends. composite -> filled diamond (*--),
                # shared -> hollow diamond (o--).
                agg = d["aggregation_kind"]
                direction = _partwhole_direction(layout, u, v, is_self)
                arrow = _make_arrow(direction, "composition" if agg == AggregationKind.COMPOSITE else "aggregation")
                left = f'"{d.get("cardinality_target", "")}" ' if d.get("cardinality_target") else ""
                right = f' "{d.get("cardinality_source", "")}"' if d.get("cardinality_source") else ""
                label = f" : {d['name']}" if d.get("name") else ""
                lines.append(f"{tgt} {left}{arrow}{right} {src}{label}")

            elif etype_lower in _DASHED_STEREOTYPES_LOWER:
                # derivation: dashed line from material relation to relator class
                direction = _assoc_direction(layout, u, v, is_self)
                arrow = _make_arrow(direction, "dashed")
                lines.append(
                    f"{src} {arrow} {tgt} : \u00AB{etype}\u00BB"
                )

            elif etype_lower in _RELATION_STEREOTYPES_LOWER:
                direction = _assoc_direction(layout, u, v, is_self)
                arrow = _make_arrow(direction, "assoc")
                left = f'"{d.get("cardinality_source", "")}" ' if d.get("cardinality_source") else ""
                right = f' "{d.get("cardinality_target", "")}"' if d.get("cardinality_target") else ""
                label = f" : \u00AB{etype}\u00BB" if etype_lower != "relation" else ""
                lines.append(f"{src} {left}{arrow}{right} {tgt}{label}")

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


# DOT render ===========================================================
# Produces Graphviz DOT output.
#
# When every node carries view coordinates (view_x, view_y, view_width,
# view_height) from the JSON diagrams section, the renderer pins each node
# with pos="x,y!" and sets layout=neato so Graphviz skips re-layout.
# The result reproduces the original VP diagram positions exactly.
#
# When coordinates are absent (model-only JSON), the renderer omits pos
# and lets Graphviz choose the layout with its default dot engine.
#
# Coordinate conversion:
#   VP uses top-left origin, y increases downward, units = pixels.
#   Graphviz uses bottom-left origin, y increases upward, units = inches
#   at 72 dpi (points per inch).
#
#   x_dot  = (vp_x + vp_width  / 2) / 72   (centre of box, in inches)
#   y_dot  = (max_y - vp_y - vp_height / 2) / 72   (flip y, centre)
#
# Run the output with:
#   dot   -Tsvg model.dot -o model.svg          (auto-layout)
#   neato -n -Tsvg model.dot -o model.svg       (pinned positions)

_PX_PER_INCH = 72.0


def _hex_to_rgb_fillcolor(hex_color: str) -> str:
    """Return a DOT-compatible color string; pass through as-is."""
    return hex_color


class OntoUMLDotRenderer:

    @property
    def format_name(self) -> str:
        return "dot"

    def render(self, graph: nx.MultiDiGraph) -> str:
        title = graph.graph.get("model_id", "OntoUML")

        # Determine whether all nodes have view coordinates.
        has_coords = all(
            graph.nodes[n].get("view_x") is not None
            for n in graph.nodes()
        ) and graph.number_of_nodes() > 0

        # Compute max_y for coordinate flip (only needed with coords).
        max_y = 0.0
        if has_coords:
            for n, d in graph.nodes(data=True):
                bottom = (d.get("view_y") or 0) + (d.get("view_height") or 0)
                if bottom > max_y:
                    max_y = float(bottom)

        lines: list[str] = []
        lines.append(f'digraph "{title}" {{')
        lines.append('  graph [fontname="Arial" rankdir=TB overlap=false splines=ortho]')
        if has_coords:
            lines.append('  // Pinned layout — run with: neato -n -Tsvg <file.dot>')
            lines.append('  layout=neato')
        lines.append('  node [fontname="Arial" shape=box style="filled,rounded"'
                     ' margin="0.1,0.05"]')
        lines.append('  edge [fontname="Arial" fontsize=9]')
        lines.append('')

        # Nodes
        for nid, d in graph.nodes(data=True):
            alias = _safe_alias(nid)
            stereotype = d.get("stereotype") or d.get("type", "class")
            label = d.get("label", stereotype)
            color = get_color_for_class(stereotype, d.get("nature", ""))

            attrs: list[str] = [
                f'label="{_dot_escape(label)}\\n«{_dot_escape(stereotype)}»"',
                f'fillcolor="{color}"',
            ]

            if has_coords:
                vx = float(d.get("view_x") or 0)
                vy = float(d.get("view_y") or 0)
                vw = float(d.get("view_width") or 100)
                vh = float(d.get("view_height") or 40)
                cx = (vx + vw / 2) / _PX_PER_INCH
                cy = (max_y - vy - vh / 2) / _PX_PER_INCH
                w_in = vw / _PX_PER_INCH
                h_in = vh / _PX_PER_INCH
                attrs += [
                    f'pos="{cx:.4f},{cy:.4f}!"',
                    f'width="{w_in:.4f}"',
                    f'height="{h_in:.4f}"',
                    'fixedsize=true',
                ]

            lines.append(f'  {alias} [{", ".join(attrs)}]')

        lines.append('')

        # Edges
        for u, v, _k, d in graph.edges(keys=True, data=True):
            src = _safe_alias(u)
            tgt = _safe_alias(v)
            etype = d.get("type", "")
            etype_lower = etype.lower()
            agg = d.get("aggregation_kind", AggregationKind.NONE)

            edge_attrs: dict[str, str] = {}

            if etype_lower == "generalization":
                # hollow open triangle pointing at general (v)
                edge_attrs["arrowhead"] = "empty"
                edge_attrs["dir"] = "forward"
                meta = _gen_meta_from_lists(
                    d.get("genset_names", []),
                    d.get("genset_is_disjoint", []),
                    d.get("genset_is_complete", []),
                )
                if meta.strip():
                    edge_attrs["label"] = f'"{_dot_escape(meta.strip())}"'

            elif etype_lower in _PART_WHOLE_STEREOTYPES_LOWER:
                # diamond on the whole end (v = target = whole), arrow at part
                # DOT: src=part -> tgt=whole, arrowtail on src side reversed
                # Use dir=back so arrowhead is at src (part) and tail at tgt (whole)
                if etype_lower in _HOLLOW_DIAMOND_STEREOTYPES:
                    edge_attrs["arrowtail"] = "odiamond"
                else:
                    edge_attrs["arrowtail"] = "diamond"
                edge_attrs["arrowhead"] = "none"
                edge_attrs["dir"] = "back"
                card_src = d.get("cardinality_source", "")
                card_tgt = d.get("cardinality_target", "")
                label_parts = [f"«{etype}»"]
                if card_src:
                    edge_attrs["taillabel"] = f'"{card_src}"'
                if card_tgt:
                    edge_attrs["headlabel"] = f'"{card_tgt}"'
                edge_attrs["label"] = f'"{_dot_escape(label_parts[0])}"'

            elif agg in (AggregationKind.COMPOSITE, AggregationKind.SHARED):
                # Anonymous aggregation: diamond at tgt (whole)
                if agg == AggregationKind.COMPOSITE:
                    edge_attrs["arrowtail"] = "diamond"
                else:
                    edge_attrs["arrowtail"] = "odiamond"
                edge_attrs["arrowhead"] = "none"
                edge_attrs["dir"] = "back"
                card_src = d.get("cardinality_source", "")
                card_tgt = d.get("cardinality_target", "")
                if card_src:
                    edge_attrs["taillabel"] = f'"{card_src}"'
                if card_tgt:
                    edge_attrs["headlabel"] = f'"{card_tgt}"'
                name = d.get("name", "")
                if name:
                    edge_attrs["label"] = f'"{_dot_escape(name)}"'

            elif etype_lower in _DASHED_STEREOTYPES_LOWER:
                edge_attrs["style"] = "dashed"
                edge_attrs["arrowhead"] = "open"
                edge_attrs["dir"] = "forward"
                edge_attrs["label"] = f'"«{_dot_escape(etype)}»"'

            else:
                edge_attrs["arrowhead"] = "open"
                edge_attrs["dir"] = "forward"
                card_src = d.get("cardinality_source", "")
                card_tgt = d.get("cardinality_target", "")
                if card_src:
                    edge_attrs["taillabel"] = f'"{card_src}"'
                if card_tgt:
                    edge_attrs["headlabel"] = f'"{card_tgt}"'
                if etype_lower not in ("relation", ""):
                    edge_attrs["label"] = f'"«{_dot_escape(etype)}»"'
                elif d.get("name"):
                    edge_attrs["label"] = f'"{_dot_escape(d["name"])}"'

            attr_str = ", ".join(f"{k}={v}" for k, v in edge_attrs.items())
            lines.append(f'  {src} -> {tgt} [{attr_str}]')

        lines.append('}')
        return '\n'.join(lines)


def _dot_escape(s: str) -> str:
    """Escape a string for use inside a DOT double-quoted attribute."""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')