import json
import re
from typing import Any

import networkx as nx

from .utils.types import ELEMENT_LAYER, RELATIONSHIP_TYPES


_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


def _clean_id(node_id: str | int) -> str:
    """Create a PlantUML-safe alias from any node id."""
    s = _NON_ALNUM.sub("", str(node_id))
    return f"n{s}" if not s or s[0].isdigit() else s


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
    # bare macros (junctions, grouping, location)
    bare = _BARE_MACROS.get(ntype)
    if bare:
        return bare

    layer = ELEMENT_LAYER.get(ntype)
    if not layer:
        return ""

    prefix = _LAYER_TO_PREFIX.get(layer, layer)

    # strip layer prefix from type name if present
    suffix = ntype[len(prefix):] if ntype.startswith(prefix) else ntype

    return f"{prefix}_{suffix}"


def _node_label(ntype: str, name: str) -> str:
    """
    Build the display label inside the PlantUML shape.
    If the name is available, it is shown as the main label, and the type
    is shown as a smaller label above it.
    """
    if name and name != ntype:
        return f"<size:10>//\\u00ab{ntype}\\u00bb//</size>\\n{name}"
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
        lines: list[str] = ["@startuml", "!include <archimate/Archimate>", ""]

        if title:
            lines += [f"title {title}", ""]

        alias_of: dict = {}

        # Nodes
        for nid, attr in graph.nodes(data=True):
            ntype = attr.get("type", "")
            name  = attr.get("label", "")
            alias = _clean_id(nid)
            alias_of[nid] = alias

            macro = _node_macro(ntype)
            label = _node_label(ntype, name)

            if macro:
                lines.append(f'{macro}("{alias}", "{label}")')
            else:
                # unknown type → visible grey rectangle + comment
                lines.append(f"' WARNING: unknown element type '{ntype}'")
                lines.append(f'rectangle "{label}" as "{alias}" #LightGray')

        lines.append("")

        # Edges
        for u, v, _k, attr in graph.edges(keys=True, data=True):
            rtype = attr.get("type", "")
            src   = alias_of.get(u)
            tgt   = alias_of.get(v)

            if src is None or tgt is None:
                lines.append(f"' WARNING: dangling edge ({u} -> {v})")
                continue

            if rtype in RELATIONSHIP_TYPES:
                lines.append(f'Rel_{rtype}("{src}", "{tgt}")')
            else:
                lines.append(f"' WARNING: unknown relationship type '{rtype}'")
                lines.append(f'"{src}" --> "{tgt}"')

        lines += ["", "@enduml"]
        return "\n".join(lines)