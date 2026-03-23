import json
from typing import Any

import networkx as nx

from .utils.types import RELATION_STEREOTYPES

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

            if etype == "generalization":
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
                if d.get("type") != "generalization":
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
            "skin rose",
        ]

        class_counter: dict[str, int] = {}

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

        for u, v, _k, d in graph.edges(keys=True, data=True):
            src = _safe_alias(u)
            tgt = _safe_alias(v)
            etype = d.get("type", "")

            if etype == "generalization":
                meta = _gen_meta_from_lists(
                    d.get("genset_names", []),
                    d.get("genset_is_disjoint", []),
                    d.get("genset_is_complete", []),
                )
                lines.append(f"{tgt} <|-- {src}: Generalization{meta}")

            elif etype in RELATION_STEREOTYPES or etype == "relation":
                card_src = d.get("cardinality_source", "")
                card_tgt = d.get("cardinality_target", "")
                left_q = f'"{card_src}" ' if card_src else ""
                right_q = f' "{card_tgt}"' if card_tgt else ""
                lines.append(
                    f'{src} {left_q}-->{right_q} {tgt}: <<{etype}>>'
                )

            elif etype == "restrictedTo":
                lines.append(
                    f'{src} .[#blue,dotted,thickness=2]. {tgt}: restrictedTo'
                )

            else:
                lines.append(f"{src} --> {tgt}: {etype}")

        lines.append("hide circle")
        lines.append("hide members")
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