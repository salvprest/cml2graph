import json
import re
from typing import Any
from collections import Counter

import networkx as nx

from .utils.types import ELEMENT_LAYER, RELATIONSHIP_TYPES


_NON_ALNUM = re.compile(r"[^A-Za-z0-9_]")

_DEFAULT_HIGHLIGHT_COLOR = "#FF4444"


def _get_highlight_color(data: dict) -> str:
    """Return the fill highlight color if present, else ``''``."""
    if data.get("highlight"):
        return data.get("highlight_color", "")
    return ""


def _get_highlight_line_color(data: dict) -> str:
    """Return the line highlight color if present, else ``''``.

    Only uses ``highlight_line_color`` — does NOT fall back to ``highlight_color``
    (that is for fill only).
    """
    if not data.get("highlight"):
        return ""
    return data.get("highlight_line_color", "")


def _is_highlighted(data: dict) -> bool:
    return bool(data.get("highlight"))


def _clean_id(node_id: str | int) -> str:
    """Create a PlantUML-safe alias from any node id.

    Must produce a valid PlantUML identifier:
    - Only alphanumeric + underscore
    - Must start with a letter
    - NEVER wrapped in quotes when used in macros
    """
    s = _NON_ALNUM.sub("_", str(node_id))
    if not s or not s[0].isalpha():
        s = f"n{s}"
    return s


# Types whose PlantUML macro is just the type name itself
_BARE_MACROS: dict[str, str] = {
    "Junction":    "Junction_And",
    "AndJunction": "Junction_And",
    "OrJunction":  "Junction_Or",
    "Grouping":    "Grouping",
    "Location":    "Location",
}

# ELEMENT_LAYER uses full layer names; PlantUML macros need short prefixes
_LAYER_TO_PREFIX: dict[str, str] = {
    "Strategy":       "Strategy",
    "Business":       "Business",
    "Application":    "Application",
    "Technology":     "Technology",
    "Physical":       "Physical",
    "Motivation":     "Motivation",
    "Implementation": "Implementation",
    "Composite":      "Other",
    "Other":          "Other",
}


def _node_macro(ntype: str) -> str:
    """
    Derive the PlantUML macro name from an ArchiMate element type.
    Examples:

        BusinessProcess       -> Business_Process
        DataObject            -> Application_DataObject
        SystemSoftware        -> Technology_SystemSoftware
        Junction              -> Junction_And
        Grouping              -> Grouping
    """
    bare = _BARE_MACROS.get(ntype)
    if bare:
        return bare

    layer = ELEMENT_LAYER.get(ntype)
    if not layer:
        return ""

    prefix = _LAYER_TO_PREFIX.get(layer, layer)
    suffix = ntype[len(prefix):] if ntype.startswith(prefix) else ntype

    return f"{prefix}_{suffix}"


def _node_label(ntype: str, display_name: str) -> str:
    """
    Build the display label inside the PlantUML shape.
    If the name is available, it is shown as the main label, and the type
    is shown as a smaller label above it.
    """
    if display_name and display_name != ntype:
        return display_name
    return ntype


class ArchiMatePlantUMLRenderer:
    """
    PlantUML renderer for ArchiMate graphs.
    Works with both rich graphs and gSpan skeletons.

    Shapes and colors are always correct because they depend only
    on type.  Names appear when available, otherwise the type
    name is shown as the label.
    """

    @property
    def format_name(self) -> str:
        return "plantuml"

    def render(self, graph: nx.MultiDiGraph, *, title: str | None = None) -> str:
        # Defer header lines — we only add the ArchiMate include when at least
        # one node uses a real ArchiMate macro (plain rectangles don't need it
        # and it actually causes a fatal parsing error on recent PlantUML builds).
        node_lines: list[str] = []
        edge_lines: list[str] = []

        diagram_title = title or graph.graph.get("model_id", "ArchiMate")

        alias_of: dict = {}
        # Tracks aliases declared as plain `rectangle` (not ArchiMate macros).
        # Edges involving these nodes cannot use Rel_* macros.
        fallback_aliases: set[str] = set()

        # Skeleton detection, auto-labeling
        type_counts: Counter[str] = Counter(
            attr.get("type", "unknown")
            for _, attr in graph.nodes(data=True)
        )
        type_index: dict[str, int] = {}

        # Nodes
        for nid, attr in graph.nodes(data=True):
            ntype = attr.get("type", "")
            name  = attr.get("label", "")
            alias = _clean_id(nid)
            alias_of[nid] = alias

            # Determine display name
            is_skeleton_node = (not name) or (name == ntype) or (name == str(nid))
            if is_skeleton_node:
                if type_counts[ntype] > 1:
                    idx = type_index.get(ntype, 0)
                    type_index[ntype] = idx + 1
                    display_name = f"{ntype}_{idx}"
                else:
                    display_name = ntype
            else:
                display_name = name

            macro = _node_macro(ntype)
            # Guarantee a non-empty label; fall back to the alias so PlantUML
            # never sees `archimate "" as n0` which confuses the parser.
            label = _node_label(ntype, display_name) or display_name or alias
            highlight_color = _get_highlight_color(attr)
            highlighted = _is_highlighted(attr)

            if macro and not highlighted:
                # Real ArchiMate element — use the stdlib macro
                node_lines.append(f'{macro}({alias}, "{label}")')
            else:
                # Unknown/typeless node OR highlighted node: use the `archimate`
                # keyword so we can specify the fill colour directly.
                color = highlight_color if highlight_color else "#LightGray"
                label_content = f'"<b>{label}</b>"' if highlighted else f'"{label}"'
                if highlighted:
                    node_lines.append(f'archimate {color} {label_content} as {alias} ##[bold]')
                else:
                    node_lines.append(f'archimate {color} {label_content} as {alias}')
                fallback_aliases.add(alias)

        # Edges
        for u, v, _k, attr in graph.edges(keys=True, data=True):
            rtype = attr.get("type", "")
            src   = alias_of.get(u)
            tgt   = alias_of.get(v)

            if src is None or tgt is None:
                edge_lines.append(f"' WARNING: dangling edge ({u} -> {v})")
                continue

            edge_highlight_color = _get_highlight_line_color(attr)
            edge_highlighted = _is_highlighted(attr)
            uses_fallback = src in fallback_aliases or tgt in fallback_aliases
            if rtype in RELATIONSHIP_TYPES and not uses_fallback and not edge_highlighted:
                # Both endpoints are proper ArchiMate macro elements
                edge_lines.append(f'Rel_{rtype}({src}, {tgt})')
            else:
                # Highlighted edge, fallback node endpoint, or unknown type
                label_suffix = f": {rtype}" if rtype else ""
                if edge_highlighted:
                    opts: list[str] = []
                    if edge_highlight_color:
                        opts.append(edge_highlight_color)
                    opts.append("thickness=4")
                    edge_lines.append(f'{src} -[{",".join(opts)}]-> {tgt}{label_suffix}')
                else:
                    edge_lines.append(f'{src} --> {tgt}{label_suffix}')

        # Include the ArchiMate stdlib only when real macro elements are present;
        # it causes a fatal parse error on recent PlantUML builds when no macro
        # elements exist.
        uses_archimate_macros = len(fallback_aliases) < graph.number_of_nodes()
        header = ["@startuml"]
        if uses_archimate_macros:
            header.append("!include <archimate/Archimate>")
        header += ["", f"title {diagram_title}", ""]

        return "\n".join(header + node_lines + [""] + edge_lines + ["", "@enduml"])