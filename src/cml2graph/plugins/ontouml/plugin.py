from collections.abc import Callable

from typing import Any
import networkx as nx

from cml2graph.core.formats import GSpanFormat
from cml2graph.core.language_schema import Renderer
from cml2graph.core.utils.pattern_enricher import is_graph_skeleton, auto_label_nodes

from .parser import parse as _parse
from . import prompts as _prompts
from .utils.types import STEREOTYPE_CATEGORY
from .filters import (
    by_stereotype,
    by_category,
    by_relationship_type,
    by_nature,
    without_orphans,
    exclude_node_types,
    exclude_edge_types,
    normalize_types,
)
from .renderer import OntoUMLJsonRenderer, OntoUMLPlantUMLRenderer
from .validator import validate_model, Issue


class OntoUMLPlugin:
    """
    OntoUML language plugin.
    Satisfies the LanguagePlugin protocol.
    """

    def __init__(self) -> None:
        self._renderers: dict[str, Renderer] = {
            "plantuml": OntoUMLPlantUMLRenderer(),
            "json": OntoUMLJsonRenderer(),
            "gspan": GSpanFormat(),
        }

    @property
    def name(self) -> str:
        return "ontouml"

    def parse(self, source: str) -> nx.MultiDiGraph:
        return _parse(source)

    def get_filters(self) -> dict[str, Callable]:
        return {
            "by_stereotype": by_stereotype,
            "by_category": by_category,
            "by_relationship_type": by_relationship_type,
            "by_nature": by_nature,
            "without_orphans": without_orphans,
            "exclude_node_types": exclude_node_types,
            "exclude_edge_types": exclude_edge_types,
            "normalize_types": normalize_types,
        }

    def is_valid(self, data: dict[str, Any]) -> bool:
        """ Check if data represents a valid OntoUML model."""
        if not isinstance(data, dict):
            return False

        issues = validate_model(data)
        errors = [i for i in issues if i.severity == "error"]
        return len(errors) == 0

    def render(self, graph: nx.MultiDiGraph, fmt_name: str | None = None) -> str:
        renderers = self.get_renderers()
        if fmt_name is None:
            fmt_name = next(iter(renderers))
        renderer = renderers.get(fmt_name)
        if renderer is None:
            raise ValueError(
                f"Unknown format '{fmt_name}'. Available: {list(renderers)}"
            )
        return renderer.render(graph)

    def get_renderers(self) -> dict[str, Renderer]:
        return dict(self._renderers)

    def get_tool_meta(self) -> dict[str, dict]:
        return _prompts.FILTER_TOOLS

    def get_general_prompt(self, graph: nx.MultiDiGraph) -> str:
        ctx = _prompts.build_prompt_context(graph)
        return _prompts.GENERAL_PROMPT.format(**ctx)

    def enrich_pattern(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        """Enrich a TVE graph data skeleton with OntoUML-specific attributes.

        Adds stereotype, category, and unique display labels so the
        PlantUML renderer produces correct output.
        """
        if not is_graph_skeleton(graph):
            return graph

        graph = auto_label_nodes(graph)

        for _, data in graph.nodes(data=True):
            ntype = data.get("type", "")
            # Add stereotype if missing
            if "stereotype" not in data:
                data["stereotype"] = ntype
            # Add category if missing
            if "category" not in data:
                data["category"] = STEREOTYPE_CATEGORY.get(ntype, "")

        # Normalize edge labels to lowercase for case-insensitive matching
        for _, _, data in graph.edges(data=True):
            if "label" not in data:
                data["label"] = data.get("type", "")

        return graph