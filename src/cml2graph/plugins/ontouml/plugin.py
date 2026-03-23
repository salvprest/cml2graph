from collections.abc import Callable

import networkx as nx

from cml2graph.core.formats import GSpanFormat
from cml2graph.core.language_schema import Renderer

from .parser import parse as _parse
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
        """Parse an OntoUML JSON file into a canonical MultiDiGraph."""
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