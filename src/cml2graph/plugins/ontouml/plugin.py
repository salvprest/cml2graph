from collections.abc import Callable

from typing import Any
import networkx as nx

from cml2graph.core.formats import GSpanFormat
from cml2graph.core.language_schema import Renderer
from cml2graph.core.utils.pattern_enricher import is_graph_skeleton, auto_label_nodes

from .parser import parse as _parse
from . import prompts as _prompts
from .utils.types import STEREOTYPE_CATEGORY, DEFAULT_NATURE_BY_STEREOTYPE, NATURE_TYPES
from .filters import (
    by_stereotype,
    by_category,
    by_relation,
    by_generalization,
    by_ontological_nature,
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
            "by_relation": by_relation,
            "by_generalization": by_generalization,
            "by_ontological_nature": by_ontological_nature,
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

        # Pre-pass: CMiner may reorder labels alphabetically, so labels[0]
        # (used as "type" by gspan_fmt) might be a nature value instead of
        # the actual stereotype.  Fix type/label before auto_label_nodes.
        for _, data in graph.nodes(data=True):
            labels = data.get("labels", [])
            if len(labels) >= 2:
                current_type = data.get("type", "")
                if current_type not in STEREOTYPE_CATEGORY:
                    # Current type is not a known stereotype — find the
                    # actual stereotype among the other labels.
                    for lab in labels:
                        if lab in STEREOTYPE_CATEGORY:
                            data["type"] = lab
                            data["label"] = lab
                            break

        graph = auto_label_nodes(graph)

        for _, data in graph.nodes(data=True):
            ntype = data.get("type", "")
            # Add stereotype if missing
            if "stereotype" not in data:
                data["stereotype"] = ntype
            # Add category if missing
            if "category" not in data:
                data["category"] = STEREOTYPE_CATEGORY.get(ntype, "")
            # Add nature if missing-critical for OntoUML color rendering.
            # Reconstruct from labels (e.g. from CMiner multi-label output)
            # before falling back to the default stereotype->nature mapping.
            if "nature" not in data:
                labels = data.get("labels", [])
                reconstructed = ""
                for lab in labels:
                    if lab != ntype and lab in NATURE_TYPES:
                        reconstructed = lab
                        break
                data["nature"] = reconstructed or DEFAULT_NATURE_BY_STEREOTYPE.get(
                    ntype.lower(), ""
                )

        # Normalize edge labels to lowercase for case-insensitive matching
        for _, _, data in graph.edges(data=True):
            if "label" not in data:
                data["label"] = data.get("type", "")

        return graph