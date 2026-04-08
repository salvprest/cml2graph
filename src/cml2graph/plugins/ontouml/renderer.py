import json
from typing import Any

import networkx as nx

from .utils.types import RELATION_STEREOTYPES, PART_WHOLE_STEREOTYPES
_RELATION_STEREOTYPES_LOWER: frozenset[str] = frozenset(
    s.lower() for s in RELATION_STEREOTYPES
)
_PART_WHOLE_STEREOTYPES_LOWER: frozenset[str] = frozenset(
    s.lower() for s in PART_WHOLE_STEREOTYPES
)

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


class OntoUMLPlantUMLRenderer:

    @property
    def format_name(self) -> str:
        return "plantuml"

    def render(self, graph: nx.MultiDiGraph) -> str:
        lines: list[str] = [
            "@startuml",
            f"title {graph.graph.get('model_id', 'OntoUML')}",
            "",
            "' OntoUML formatting",
            "skinparam roundcorner 10",
            "skinparam classBorderColor #333333",
            "skinparam classFontName Arial",
            "skinparam shadowing false",
            "hide circle",
            "hide members",
            "",
            "' Straight line routing",
            "skinparam linetype ortho",
            "skinparam nodesep 60",
            "skinparam ranksep 60",
            "",
            "' OntoUML Smart Paint Color Palette",
            "skinparam class {",
            "    BackgroundColor<<kind>> #FFB6C1",
            "    BackgroundColor<<subkind>> #FFB6C1",
            "    BackgroundColor<<collective>> #FFB6C1",
            "    BackgroundColor<<quantity>> #FFB6C1",
            "    BackgroundColor<<role>> #FFFFCC",
            "    BackgroundColor<<phase>> #FFFFCC",
            "    BackgroundColor<<historicalRole>> #FFFFCC",
            "    BackgroundColor<<category>> #E0FFFF",
            "    BackgroundColor<<mixin>> #E0FFFF",
            "    BackgroundColor<<roleMixin>> #E0FFFF",
            "    BackgroundColor<<phaseMixin>> #E0FFFF",
            "    BackgroundColor<<historicalRoleMixin>> #E0FFFF",
            "    BackgroundColor<<abstract>> #E0FFFF",
            "    BackgroundColor<<relator>> #CCFFCC",
            "    BackgroundColor<<mode>> #E6E6FA",
            "    BackgroundColor<<quality>> #E6E6FA",
            "    BackgroundColor<<event>> #F08080",
            "    BackgroundColor<<situation>> #F08080",
            "    BackgroundColor<<datatype>> #FFDAB9",
            "    BackgroundColor<<enumeration>> #FFDAB9",
            "    BackgroundColor<<type>> #FFDAB9",
            "}",
            "",
        ]

        class_counter: dict[str, int] = {}

        # Nodes
        for nid, d in graph.nodes(data=True):
            alias = _safe_alias(nid)
            stereotype = d.get("stereotype") or d.get("type", "class")
            name = d.get("label", stereotype)
            is_skeleton = (name == stereotype) or (name == str(nid))

            if is_skeleton:
                idx = class_counter.get(stereotype, 0)
                class_counter[stereotype] = idx + 1
                display = f"{stereotype}_{idx}"
            else:
                display = name

            lines.append(
                f'class "{display}" as {alias} <<{stereotype}>>'
            )

        lines.append("")

        # Edges
        for u, v, _k, d in graph.edges(keys=True, data=True):
            src = _safe_alias(u)
            tgt = _safe_alias(v)
            etype = d.get("type", "")
            etype_lower = etype.lower()

            if etype_lower == "generalization":
                meta = _gen_meta_from_lists(
                    d.get("genset_names", []),
                    d.get("genset_is_disjoint", []),
                    d.get("genset_is_complete", []),
                )
                if meta:
                    lines.append(f"{src} -up-|> {tgt} :{meta}")
                else:
                    lines.append(f"{src} -up-|> {tgt}")

            elif etype_lower in _PART_WHOLE_STEREOTYPES_LOWER:
                card_src = d.get("cardinality_source", "")
                card_tgt = d.get("cardinality_target", "")
                left_q = f'"{card_tgt}" ' if card_tgt else ""
                right_q = f' "{card_src}"' if card_src else ""
                arrow = "*-up-" if src == tgt else "*-down-"
                lines.append(
                    f'{tgt} {left_q}{arrow}{right_q} {src} : \u00AB{etype}\u00BB'
                )

            elif etype_lower in _RELATION_STEREOTYPES_LOWER:
                card_src = d.get("cardinality_source", "")
                card_tgt = d.get("cardinality_target", "")
                left_q = f'"{card_src}" ' if card_src else ""
                right_q = f' "{card_tgt}"' if card_tgt else ""
                # Hide label for the generic "relation" stereotype
                if etype_lower != "relation":
                    label = f' : \u00AB{etype}\u00BB'
                else:
                    label = ""
                arrow = "-up->" if src == tgt else "-->"
                lines.append(
                    f'{src} {left_q}{arrow}{right_q} {tgt}{label}'
                )

            elif etype_lower == "restrictedto":
                lines.append(
                    f'{src} .[#888888].> {tgt} : restrictedTo'
                )

            else:
                card_src = d.get("cardinality_source", "")
                card_tgt = d.get("cardinality_target", "")
                left_q = f'"{card_src}" ' if card_src else ""
                right_q = f' "{card_tgt}"' if card_tgt else ""
                label = f" : {etype}" if etype else ""
                arrow = "-up->" if src == tgt else "-->"
                lines.append(f'{src} {left_q}{arrow}{right_q} {tgt}{label}')

        lines.append("")
        lines.append("@enduml")
        return "\n".join(lines)



def _safe_alias(node_id: Any) -> str:
    """
    PlantUML-safe alias:
    - Replace non-alnum with _
    - Prefix N so it always starts with a letter
    """
    s = str(node_id)
    cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in s)
    return f"N{cleaned}" if cleaned else "Nnode"


def _gen_meta_from_lists(names: list[str], disjoint_flags: list[bool], complete_flags: list[bool]) -> str:
    """
    Build annotation from ALL gensets this generalization belongs to.
    Example output: " PersonTypes {disjoint} | LivingThings {complete}"
    """
    if not names and not disjoint_flags and not complete_flags:
        return ""

    segments: list[str] = []
    count = max(len(names), len(disjoint_flags), len(complete_flags), 0)

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

    if segments:
        return " " + " | ".join(segments)
    return ""