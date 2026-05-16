from collections.abc import Callable

from typing import Any
import networkx as nx

from .parser import parse as _parse
from .filters import get_filters as _get_filters
from .renderer import ArchiMatePlantUMLRenderer
from . import prompts as _prompts
from .validator import validate_model, Issue
from .utils.types import ELEMENT_LAYER

from cml2graph.core.formats.gspan_fmt import GSpanFormat
from cml2graph.core.language_schema import Renderer
from cml2graph.core.utils.pattern_enricher import is_graph_skeleton, auto_label_nodes

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

    def enrich_pattern(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        """Enrich a TVE graph data skeleton with ArchiMate-specific attributes.

        Adds layer and unique display labels so the PlantUML renderer
        produces correct ArchiMate diagrams.
        """
        if not is_graph_skeleton(graph):
            return graph

        graph = auto_label_nodes(graph)

        for _, data in graph.nodes(data=True):
            ntype = data.get("type", "")
            # Add layer if missing — critical for ArchiMate rendering.
            # Try to reconstruct from labels (e.g. from CMiner multi-label output)
            # before falling back to the type->layer mapping.
            if "layer" not in data:
                labels = data.get("labels", [])
                _layer_values = set(ELEMENT_LAYER.values())
                reconstructed = ""
                for lab in labels:
                    if lab != ntype and lab in _layer_values:
                        reconstructed = lab
                        break
                data["layer"] = reconstructed or ELEMENT_LAYER.get(ntype, "Other")

        for _, _, data in graph.edges(data=True):
            if "label" not in data:
                data["label"] = data.get("type", "")

        return graph