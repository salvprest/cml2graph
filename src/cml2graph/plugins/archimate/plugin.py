from collections.abc import Callable

from typing import Any
import networkx as nx

from .parser import parse as _parse
from .filters import get_filters as _get_filters
from .renderer import ArchiMatePlantUMLRenderer
from . import prompts as _prompts
from .validator import validate_model, Issue

from cml2graph.core.formats.gspan_fmt import GSpanFormat
from cml2graph.core.language_schema import Renderer

class ArchiMatePlugin:
    """ArchiMate LanguagePlugin Protocol implementation."""

    def __init__(self) -> None:
        self._renderers: dict[str, Renderer] = {
            "plantuml": ArchiMatePlantUMLRenderer(),
            "gspan": GSpanFormat(), # TODO: very ugly this should not be here
        }

    @property
    def name(self) -> str:
        return "archimate"

    def parse(self, source: str) -> nx.MultiDiGraph:
        return _parse(source)

    def get_filters(self) -> dict[str, Callable]:
        return _get_filters()

    def is_valid(self, data: dict[str, Any]) -> bool:
        """
        Check if data represents a valid ArchiMate model.
        """
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
        """Filter metadata keyed by filter name."""
        return _prompts.FILTER_TOOLS

    def get_general_prompt(self, graph: nx.MultiDiGraph) -> str:
        ctx = _prompts.build_prompt_context(graph)
        return _prompts.GENERAL_PROMPT.format(**ctx)