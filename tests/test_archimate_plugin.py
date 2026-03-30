"""
Tests for the ArchiMate plugin.

Covers parser, validator, renderer, filters, plugin end-to-end,
and prompts metadata consistency.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import networkx as nx
import pytest

from cml2graph.plugins.archimate.plugin import ArchiMatePlugin
from cml2graph.plugins.archimate.parser import parse
from cml2graph.plugins.archimate.validator import validate_model
from cml2graph.plugins.archimate.renderer import ArchiMatePlantUMLRenderer
from cml2graph.plugins.archimate.filters import (
    by_layer,
    by_element_type,
    by_relationship_type,
    without_orphans,
)
from cml2graph.plugins.archimate.prompts import FILTER_TOOLS
from cml2graph.core.language_schema import LanguagePlugin


FIXTURE = Path(__file__).parent / "fixtures" / "simple_model.json"


# ── pytest fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def graph() -> nx.MultiDiGraph:
    return parse(str(FIXTURE))


@pytest.fixture
def renderer() -> ArchiMatePlantUMLRenderer:
    return ArchiMatePlantUMLRenderer()


@pytest.fixture
def plugin() -> ArchiMatePlugin:
    return ArchiMatePlugin()


# ── protocol ──────────────────────────────────────────────────────────────────

def test_plugin_satisfies_protocol():
    assert isinstance(ArchiMatePlugin(), LanguagePlugin)


# ── parsing ───────────────────────────────────────────────────────────────────

def test_parse_returns_multidigraph():
    g = parse(str(FIXTURE))
    assert isinstance(g, nx.MultiDiGraph)


def test_parse_node_count():
    g = parse(str(FIXTURE))
    assert g.number_of_nodes() == 4


def test_parse_edge_count():
    g = parse(str(FIXTURE))
    assert g.number_of_edges() == 3


def test_parse_model_id():
    g = parse(str(FIXTURE))
    assert g.graph["model_id"] == "model-001"


def test_parse_node_attributes():
    g = parse(str(FIXTURE))
    e1 = g.nodes["e1"]
    assert e1["id"] == "e1"
    assert e1["type"] == "ApplicationService"
    assert e1["label"] == "OrderService"
    assert e1["layer"] == "Application"


def test_parse_edge_attributes():
    g = parse(str(FIXTURE))
    edge_data = g.get_edge_data("e1", "e3", "r1")
    assert edge_data is not None
    assert edge_data["type"] == "Serving"
    assert edge_data["label"] == "Serving"


def test_parse_missing_file_raises():
    with pytest.raises(ValueError, match="Cannot read"):
        parse("/nonexistent/path/model.json")


def test_parse_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse(str(bad))


def test_parse_missing_elements_key_raises(tmp_path):
    bad = tmp_path / "model.json"
    bad.write_text(json.dumps({"relationships": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="Validation failed"):
        parse(str(bad))


# ── validator ─────────────────────────────────────────────────────────────────

def test_validate_clean_model():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    issues = validate_model(data)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


# ── renderer ──────────────────────────────────────────────────────────────────

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
    assert "rectangle" in result


# ── filters ───────────────────────────────────────────────────────────────────

def test_by_layer_keeps_matching_nodes(graph):
    sub = by_layer(graph, "Application")
    layers = {d["layer"] for _, d in sub.nodes(data=True)}
    assert layers == {"Application"}


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
    graph.add_node("orphan", id="orphan", type="BusinessActor", label="Nobody", layer="Business")
    assert graph.has_node("orphan")
    sub = without_orphans(graph)
    assert not sub.has_node("orphan")


def test_without_orphans_keeps_connected(graph):
    sub = without_orphans(graph)
    assert sub.number_of_nodes() == graph.number_of_nodes()


# ── plugin end-to-end ─────────────────────────────────────────────────────────

def test_plugin_render_plantuml(plugin, graph):
    result = plugin.render(graph, "plantuml")
    assert "@startuml" in result


def test_plugin_render_default_format(plugin, graph):
    result = plugin.render(graph)
    assert isinstance(result, str)
    assert len(result) > 0


def test_plugin_render_unknown_format_raises(plugin, graph):
    with pytest.raises(ValueError, match="Unknown format"):
        plugin.render(graph, "nonexistent_format")


def test_plugin_get_filters_has_expected_keys(plugin):
    filters = plugin.get_filters()
    assert "by_layer" in filters
    assert "by_element_type" in filters
    assert "by_relationship_type" in filters
    assert "without_orphans" in filters


# ── prompts metadata ──────────────────────────────────────────────────────────

def test_filter_tools_keys_match_get_filters():
    """Every key in FILTER_TOOLS must correspond to a real filter function."""
    filters = ArchiMatePlugin().get_filters()
    for name in FILTER_TOOLS:
        assert name in filters, (
            f"FILTER_TOOLS has '{name}' but get_filters() does not"
        )


def test_filter_tools_param_names_match_signatures():
    """Param names in FILTER_TOOLS must match the filter function signatures
    so that **args unpacking works at call time."""
    filters = ArchiMatePlugin().get_filters()
    for filter_name, meta in FILTER_TOOLS.items():
        sig_params = set(inspect.signature(filters[filter_name]).parameters) - {"graph"}
        meta_params = set(meta.get("params", {}).keys())
        assert meta_params <= sig_params, (
            f"Filter '{filter_name}': metadata params {meta_params} "
            f"not a subset of signature params {sig_params}"
        )


def test_filter_tools_params_have_type_field():
    """All params with an enum should carry a 'type' field for schema generation."""
    for filter_name, meta in FILTER_TOOLS.items():
        for param_name, param_meta in meta.get("params", {}).items():
            if "enum" in param_meta:
                assert "type" in param_meta, (
                    f"Filter '{filter_name}', param '{param_name}' "
                    f"has 'enum' but no 'type'"
                )


def test_filter_tools_enums_are_non_empty():
    """Every enum list in FILTER_TOOLS must be non-empty."""
    for filter_name, meta in FILTER_TOOLS.items():
        for param_name, param_meta in meta.get("params", {}).items():
            if "enum" in param_meta:
                assert len(param_meta["enum"]) > 0, (
                    f"Filter '{filter_name}', param '{param_name}' has empty enum"
                )
