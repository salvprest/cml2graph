import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx

from .validator import Issue, validate_model
from .utils.helpers import extract_contents, ref_id
from .utils.types import (
    ASSOCIATION_NAME_SYNONYMS,
    STEREOTYPE_CATEGORY,
)

logger = logging.getLogger(__name__)

def parse(source: str) -> nx.MultiDiGraph:
    """Parse an OntoUML JSON file into a canonical nx.MultiDiGraph."""
    path = Path(source)
    raw = json.loads(path.read_text(encoding="utf-8"))

    issues = validate_model(raw)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        msg = "; ".join(str(e) for e in errors)
        raise ValueError(msg)

    return _build_graph(raw, model_id=path.stem, issues=issues)


def _build_graph( data: dict[str, Any], model_id: str, issues: list[Issue]) -> nx.MultiDiGraph:
    """Build the graph from the raw JSON data."""
    G = nx.MultiDiGraph()
    G.graph["model_id"] = model_id

    contents = extract_contents(data) or []

    # index by type
    classes: dict[str, dict] = {}
    relations: list[dict] = []
    generalizations: list[dict] = []
    gen_sets: list[dict] = []

    for item in contents:
        tp = item.get("type")
        if tp == "Class":
            classes[item["id"]] = item
        elif tp == "Relation":
            relations.append(item)
        elif tp == "Generalization":
            generalizations.append(item)
        elif tp == "GeneralizationSet":
            gen_sets.append(item)

    # process class nodes
    for cid, cls in classes.items():
        stereotype = cls.get("stereotype") or "class"
        name = cls.get("name") or stereotype
        nature_list = cls.get("restrictedTo") or []
        nature_str = ",".join(nature_list) if nature_list else ""
        category = STEREOTYPE_CATEGORY.get(stereotype, "")

        G.add_node(
            cid,
            id=cid,
            label=name,
            type=stereotype,
            stereotype=stereotype,
            nature=nature_str,
            category=category,
        )

    # process relations/association
    for rel in relations:
        rid = rel["id"]
        raw_name = rel.get("name") or ""
        raw_stereotype = rel.get("stereotype") or "relation"

        # Normalise informal names to canonical stereotypes
        stereotype = ASSOCIATION_NAME_SYNONYMS.get(
            raw_name,
            ASSOCIATION_NAME_SYNONYMS.get(
                raw_name.lower(), raw_stereotype
            ),
        )

        props = rel.get("properties") or []
        endpoint_ids: list[str] = []
        cardinalities: list[str] = []
        for prop in props:
            pt = prop.get("propertyType", {})
            eid = pt.get("id") if isinstance(pt, dict) else None
            if eid:
                endpoint_ids.append(eid)
            cardinalities.append(prop.get("cardinality") or "")

        if len(endpoint_ids) < 2:
            logger.warning("Relation %s has fewer than 2 endpoints, skipping", rid)
            continue

        source_id, target_id = endpoint_ids[0], endpoint_ids[1]
        if source_id not in G:
            logger.warning("Relation %s: source %s not in graph, skipping edge", rid, source_id)
            continue
        if target_id not in G:
            logger.warning("Relation %s: target %s not in graph, skipping edge", rid, target_id)
            continue
        card_source = cardinalities[0] if cardinalities else ""
        card_target = cardinalities[1] if len(cardinalities) > 1 else ""

        G.add_edge(
            source_id, target_id,
            key=rid,
            id=rid,
            type=stereotype,
            label=stereotype,
            name=raw_name,
            cardinality_source=card_source,
            cardinality_target=card_target,
        )

    # process generalization sets

    # Map each generalization ID to its parent GeneralizationSet.
    genset_index: dict[str, list[dict]] = {}
    gs_graph_meta: list[dict] = []

    for gs in gen_sets:
        gs_id = gs.get("id", "")
        gs_info: dict[str, Any] = {
            "id": gs_id,
            "name": gs.get("name") or "",
            "isDisjoint": gs.get("isDisjoint", False),
            "isComplete": gs.get("isComplete", False),
            "generalizations": [],
        }
        for g_ref in gs.get("generalizations") or {}:
            gid = g_ref.get("id", None)
            if gid:
                gs_info["generalizations"].append(gid)
                genset_index.setdefault(gid, []).append(gs_info)
        gs_graph_meta.append(gs_info)

    G.graph["generalization_sets"] = gs_graph_meta

    # process generalization
    for gen in generalizations:
        gid = gen["id"]
        general_id = ref_id(gen.get("general"))
        specific_id = ref_id(gen.get("specific"))
        if not general_id or not specific_id:
            continue

        if general_id not in G:
            logger.warning("Generalization %s: general %s not in graph, skipping", gid, general_id)
            continue
        if specific_id not in G:
            logger.warning("Generalization %s: specific %s not in graph, skipping", gid, specific_id)
            continue

        # Take the gensets this generalization belongs to
        gs_list = genset_index.get(gid, [])
        genset_ids = [gs["id"] for gs in gs_list]
        genset_names = [gs["name"] for gs in gs_list]
        genset_is_disjoint = [gs.get("isDisjoint", False) for gs in gs_list]
        genset_is_complete = [gs.get("isComplete", False) for gs in gs_list]

        G.add_edge(
            specific_id, general_id,
            key=gid,
            id=gid,
            type="generalization",
            label="generalization",
            genset_ids=genset_ids,
            genset_names=genset_names,
            genset_is_disjoint=genset_is_disjoint,
            genset_is_complete=genset_is_complete,
        )

    return G