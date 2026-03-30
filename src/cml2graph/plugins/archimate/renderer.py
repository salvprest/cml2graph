import json
import re
from typing import Any
from collections import Counter

import networkx as nx

from .utils.types import ELEMENT_LAYER, RELATIONSHIP_TYPES


_NON_ALNUM = re.compile(r"[^A-Za-z0-9_]")


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
        # Check if display_name is an auto-label like "BusinessProcess_0"
        # In that case, don't add the type annotation (it's redundant)
        if display_name.startswith(ntype):
            return display_name
        return f"<size:10>//\\u00ab{ntype}\\u00bb//</size>\\n{display_name}"
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

        diagram_title = title or graph.graph.get("model_id", "ArchiMate")
        lines.append(f"title {diagram_title}")
        lines.append("")

        alias_of: dict = {}

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
            label = _node_label(ntype, display_name)

            if macro:
                # unquoted alias, quoted label
                lines.append(f'{macro}({alias}, "{label}")')
            else:
                lines.append(f"' WARNING: unknown element type '{ntype}'")
                # unquoted alias
                lines.append(f'rectangle "{label}" as {alias} #LightGray')

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
                # unquoted, unquoted
                lines.append(f'Rel_{rtype}({src}, {tgt})')
            else:
                lines.append(f"' WARNING: unknown relationship type '{rtype}'")
                lines.append(f'{src} --> {tgt}')

        lines += ["", "@enduml"]
        return "\n".join(lines)