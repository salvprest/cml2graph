from collections.abc import Callable

from typing import Any
import networkx as nx

from cml2graph.core.formats import GSpanFormat
from cml2graph.core.language_schema import Renderer

from .parser import parse as _parse
from . import prompts as _prompts
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