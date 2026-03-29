import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx

from cml2graph.core.language_schema import GraphEdge, GraphNode
from .utils.types import ELEMENT_LAYER
from .validator import validate_model

logger = logging.getLogger(__name__)


def parse(source: str) -> nx.MultiDiGraph:
    """
    Read source (a path to a JSON file) and return a clean
    MultiDiGraph whose nodes are elements and whose
    edges are relationships.

    Raises
    ------
    ValueError
        On I/O errors, malformed JSON, or validation errors.
    """
    path = Path(source)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    # validate
    issues = validate_model(data)
    for issue in issues:
        (logger.warning if issue.severity == "warning" else logger.error)(
            "%s", issue
        )
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        summary = "\n  ".join(str(e) for e in errors)
        raise ValueError(f"Validation failed for {path}:\n  {summary}")

    return _build_graph(data)


def _build_graph(data: dict[str, Any]) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    G.graph["model_id"] = data.get("archimateId", "unknown")

    # nodes, one per element
    for elem in data["elements"]:
        eid = elem["id"]
        etype = elem["type"]
        node: GraphNode = {
            "id": eid,
            "label": elem.get("name", ""),
            "type": etype,
            "layer": ELEMENT_LAYER.get(etype),
        }
        G.add_node(eid, **node)

    # edges, one per relationship, keyed by relationship id
    for rel in data["relationships"]:
        rtype = rel["type"]
        edge: GraphEdge = {
            "id": rel["id"],
            "type": rtype,
            "label": rtype,
        }
        G.add_edge(rel["sourceId"], rel["targetId"], key=rel["id"], **edge)

    return G