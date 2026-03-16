from collections.abc import Callable

import networkx as nx

from .parser import parse as _parse
from .filters import get_filters as _get_filters
from .renderer import ArchiMatePlantUMLRenderer

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