"""Tests for core protocols and PluginManager."""
import json
import pytest
import networkx as nx

from cml2graph.core import LanguagePlugin, Renderer, FormatCodec, PluginManager


# ── Minimal stubs ────────────────────────────────────────────────────────────

class _MinimalRenderer:
    @property
    def format_name(self) -> str:
        return "dummy"

    def render(self, graph: nx.MultiDiGraph) -> str:
        return "rendered"


class _MinimalPlugin:
    @property
    def name(self) -> str:
        return "dummy"

    def parse(self, source: str) -> nx.MultiDiGraph:
        return nx.MultiDiGraph()

    def get_filters(self):
        return {}

    def is_valid(self, data):
        return True

    def render(self, graph: nx.MultiDiGraph, fmt_name=None) -> str:
        return ""

    def get_renderers(self):
        return {}


class _BadPlugin:
    """Does NOT satisfy LanguagePlugin (missing parse/get_filters/render/get_renderers)."""
    @property
    def name(self) -> str:
        return "bad"


# ── Protocol satisfaction ─────────────────────────────────────────────────────

def test_renderer_protocol_satisfied():
    assert isinstance(_MinimalRenderer(), Renderer)


def test_language_plugin_protocol_satisfied():
    assert isinstance(_MinimalPlugin(), LanguagePlugin)


def test_bad_plugin_does_not_satisfy_protocol():
    assert not isinstance(_BadPlugin(), LanguagePlugin)


# ── PluginManager ─────────────────────────────────────────────────────────────

def test_register_and_get():
    pm = PluginManager()
    pm.register(_MinimalPlugin())
    plugin = pm.get("dummy")
    assert plugin.name == "dummy"


def test_get_unknown_raises():
    pm = PluginManager()
    with pytest.raises(KeyError, match="dummy"):
        pm.get("dummy")


def test_register_bad_plugin_raises():
    pm = PluginManager()
    with pytest.raises(TypeError):
        pm.register(_BadPlugin())  # type: ignore[arg-type]


def test_register_overwrites_duplicate(caplog):
    pm = PluginManager()
    pm.register(_MinimalPlugin())
    pm.register(_MinimalPlugin())   # second registration should warn, not crash
    assert pm.get("dummy") is not None


def test_discover_archimate(tmp_path):
    """discover() can locate the built-in archimate plugin package."""
    pm = PluginManager()
    pm.discover("cml2graph.plugins")
    plugin = pm.get("archimate")
    assert plugin.name == "archimate"

def test_discover_ontouml(tmp_path):
    """discover() can locate the built-in archimate plugin package."""
    pm = PluginManager()
    pm.discover("cml2graph.plugins")
    plugin = pm.get("ontouml")


# ── NodeLinkFormat ────────────────────────────────────────────────────────────

def test_node_link_includes_nature_and_layer_in_labels():
    from cml2graph.core.formats.node_link_fmt import NodeLinkFormat

    g = nx.MultiDiGraph()
    g.add_node("a", id="a", type="kind", nature="functional-complex")
    g.add_node("b", id="b", type="BusinessProcess", layer="Business")
    g.add_node("c", id="c", type="Unknown")

    text = NodeLinkFormat().render(g)
    data = json.loads(text)

    node_by_id = {n["id"]: n for n in data["nodes"]}
    assert node_by_id["a"]["labels"] == ["kind", "functional-complex"]
    assert node_by_id["b"]["labels"] == ["BusinessProcess", "Business"]
    assert node_by_id["c"]["labels"] == ["Unknown"]


def test_node_link_preserves_existing_labels():
    from cml2graph.core.formats.node_link_fmt import NodeLinkFormat

    g = nx.MultiDiGraph()
    g.add_node("a", id="a", type="kind", labels=["custom", "label"])

    text = NodeLinkFormat().render(g)
    data = json.loads(text)

    assert data["nodes"][0]["labels"] == ["custom", "label"]