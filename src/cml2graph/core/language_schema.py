from typing import TypedDict, Protocol, runtime_checkable
from collections.abc import Callable
import networkx as nx

class GraphNode(TypedDict, total=False):
    id: str
    type: str
    label: str
    layer: str | None


class GraphEdge(TypedDict, total=False):
    id: str
    type: str
    label: str


@runtime_checkable
class Renderer(Protocol):
    """Structural type every renderer must satisfy."""

    @property
    def format_name(self) -> str:
        """Short key: 'plantuml', 'mermaid', …"""
        ...

    def render(self, graph: nx.MultiDiGraph) -> str:
        """Turn a graph into a string in this format."""
        ...

@runtime_checkable
class FormatCodec(Protocol):
    """
    Two way: graph to/from text.
    FormatCodec are general not plugin depended

    Every FormatCodec also satisfies Renderer Protocol,
    """

    @property
    def format_name(self) -> str: ...

    def render(self, graph: nx.MultiDiGraph) -> str: ...

    def parse(self, text: str) -> list[nx.MultiDiGraph]: ...


@runtime_checkable
class LanguagePlugin(Protocol):
    """Structural type that every language plugin must satisfy."""

    @property
    def name(self) -> str:
        ...

    def parse(self, source: str) -> nx.MultiDiGraph:
        """Parse a source file into a nx multigraph."""
        ...

    def get_filters(self) -> dict[str, Callable]:
        """Return language specific filter functions."""
        ...

    def render(self, graph: nx.MultiDiGraph, fmt_name: str | None = None) -> str:
        """
        Render nx multigraph to a string representation.
        If fmt_name is None use the first renderer of the get_renderers list.
        """
        ...

    def get_renderers(self) -> dict[str, Renderer]:
        """Return the renderers this plugin ships, keyed by name."""
        ...