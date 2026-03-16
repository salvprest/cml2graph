"""Tests for ArchiMate PlantUML renderer and graph filters."""
import pytest
from pathlib import Path

import networkx as nx

from cml2graph.plugins.archimate.parser import parse
from cml2graph.plugins.archimate.renderer import ArchiMatePlantUMLRenderer
from cml2graph.plugins.archimate.filters import (
    by_layer,
    by_element_type,
    by_relationship_type,
    without_orphans,
)

FIXTURE = Path(__file__).parent / "fixtures" / "simple_model.json"


@pytest.fixture
def graph() -> nx.MultiDiGraph:
    return parse(str(FIXTURE))


@pytest.fixture
def renderer() -> ArchiMatePlantUMLRenderer:
    return ArchiMatePlantUMLRenderer()


# ── Renderer ──────────────────────────────────────────────────────────────────

def test_renderer_format_name(renderer):
    assert renderer.format_name == "plantuml"


def test_renderer_output_is_string(renderer, graph):
    result = renderer.render(graph)
    assert isinstance(result, str)


def test_renderer_starts_and_ends(renderer, graph):
    result = renderer.render(graph)
    assert result.startswith("@startuml")
    assert result.strip().endswith("@enduml")


def test_renderer_contains_node_macros(renderer, graph):
    result = renderer.render(graph)
    # ApplicationService node should produce an Application_ macro
    assert "Application_" in result


def test_renderer_contains_relationship(renderer, graph):
    result = renderer.render(graph)
    assert "Rel_Serving" in result
    assert "Rel_Access" in result
    assert "Rel_Assignment" in result


def test_renderer_with_title(renderer, graph):
    result = renderer.render(graph, title="My Diagram")
    assert "title My Diagram" in result


def test_renderer_unknown_type_fallback(renderer):
    g = nx.MultiDiGraph()
    g.add_node("n1", id="n1", type="Unicorn", label="Horned creature", layer=None)
    result = renderer.render(g)
    assert "WARNING: unknown element type 'Unicorn'" in result
    assert 'rectangle' in result


# ── Filters ───────────────────────────────────────────────────────────────────

def test_by_layer_keeps_matching_nodes(graph):
    sub = by_layer(graph, "Application")
    types = {d["layer"] for _, d in sub.nodes(data=True)}
    assert types == {"Application"}


def test_by_layer_multiple_layers(graph):
    sub = by_layer(graph, ["Application", "Business"])
    layers = {d["layer"] for _, d in sub.nodes(data=True)}
    assert layers == {"Application", "Business"}


def test_by_layer_empty_result(graph):
    sub = by_layer(graph, "Technology")
    assert sub.number_of_nodes() == 0


def test_by_element_type(graph):
    sub = by_element_type(graph, "BusinessRole")
    assert sub.number_of_nodes() == 1
    node_id = list(sub.nodes())[0]
    assert sub.nodes[node_id]["type"] == "BusinessRole"


def test_by_relationship_type_keeps_edges(graph):
    sub = by_relationship_type(graph, "Serving")
    edge_types = {d["type"] for _, _, d in sub.edges(data=True)}
    assert edge_types == {"Serving"}


def test_by_relationship_type_keeps_all_nodes(graph):
    sub = by_relationship_type(graph, "Serving")
    assert sub.number_of_nodes() == graph.number_of_nodes()


def test_without_orphans_removes_isolated(graph):
    # add an isolated node then remove it
    graph.add_node("orphan", id="orphan", type="BusinessActor", label="Nobody", layer="Business")
    assert graph.has_node("orphan")
    sub = without_orphans(graph)
    assert not sub.has_node("orphan")


def test_without_orphans_keeps_connected(graph):
    sub = without_orphans(graph)
    assert sub.number_of_nodes() == graph.number_of_nodes()


# ── ArchiMatePlugin end-to-end ────────────────────────────────────────────────

def test_plugin_render_plantuml():
    from cml2graph.plugins.archimate import ArchiMatePlugin
    plugin = ArchiMatePlugin()
    g = parse(str(FIXTURE))
    result = plugin.render(g, "plantuml")
    assert "@startuml" in result


def test_plugin_render_default_format():
    from cml2graph.plugins.archimate import ArchiMatePlugin
    plugin = ArchiMatePlugin()
    g = parse(str(FIXTURE))
    result = plugin.render(g)
    assert isinstance(result, str)
    assert len(result) > 0


def test_plugin_render_unknown_format_raises():
    from cml2graph.plugins.archimate import ArchiMatePlugin
    plugin = ArchiMatePlugin()
    g = parse(str(FIXTURE))
    with pytest.raises(ValueError, match="Unknown format"):
        plugin.render(g, "nonexistent_format")


def test_plugin_get_filters_has_expected_keys():
    from cml2graph.plugins.archimate import ArchiMatePlugin
    plugin = ArchiMatePlugin()
    filters = plugin.get_filters()
    assert "by_layer" in filters
    assert "by_element_type" in filters
    assert "by_relationship_type" in filters
    assert "without_orphans" in filters
