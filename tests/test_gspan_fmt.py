"""Tests for GSpanFormat (core/formats/gspan_fmt.py)."""
import pytest
import networkx as nx

from cml2graph.core.formats.gspan_fmt import GSpanFormat, PatternResult


@pytest.fixture
def fmt() -> GSpanFormat:
    return GSpanFormat()


@pytest.fixture
def simple_graph() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    g.graph["model_id"] = "m1"
    g.add_node("a", id="a", type="BusinessRole", label="Actor")
    g.add_node("b", id="b", type="ApplicationService", label="Service")
    g.add_edge("a", "b", type="Serving", label="Serving")
    return g


# ── Renderer interface ────────────────────────────────────────────────────────

def test_format_name(fmt):
    assert fmt.format_name == "gspan"


def test_render_returns_string(fmt, simple_graph):
    result = fmt.render(simple_graph)
    assert isinstance(result, str)


def test_render_has_t_line(fmt, simple_graph):
    result = fmt.render(simple_graph)
    assert result.startswith("t # ")


def test_render_has_v_lines(fmt, simple_graph):
    result = fmt.render(simple_graph)
    lines = result.splitlines()
    v_lines = [l for l in lines if l.startswith("v ")]
    assert len(v_lines) == 2


def test_render_has_e_lines(fmt, simple_graph):
    result = fmt.render(simple_graph)
    lines = result.splitlines()
    e_lines = [l for l in lines if l.startswith("e ")]
    assert len(e_lines) == 1


def test_render_contains_types(fmt, simple_graph):
    result = fmt.render(simple_graph)
    assert "BusinessRole" in result
    assert "ApplicationService" in result
    assert "Serving" in result


# ── Round-trip ────────────────────────────────────────────────────────────────

def test_roundtrip_node_count(fmt, simple_graph):
    text = fmt.render(simple_graph)
    graphs = fmt.parse(text)
    assert len(graphs) == 1
    assert graphs[0].number_of_nodes() == 2


def test_roundtrip_edge_count(fmt, simple_graph):
    text = fmt.render(simple_graph)
    graphs = fmt.parse(text)
    assert graphs[0].number_of_edges() == 1


def test_roundtrip_node_types(fmt, simple_graph):
    text = fmt.render(simple_graph)
    graphs = fmt.parse(text)
    types = {d["type"] for _, d in graphs[0].nodes(data=True)}
    assert "BusinessRole" in types
    assert "ApplicationService" in types


def test_roundtrip_edge_type(fmt, simple_graph):
    text = fmt.render(simple_graph)
    graphs = fmt.parse(text)
    edge_types = {d["type"] for _, _, d in graphs[0].edges(data=True)}
    assert "Serving" in edge_types


# ── render_corpus + parse ─────────────────────────────────────────────────────

def test_corpus_roundtrip(fmt, simple_graph):
    g2 = nx.MultiDiGraph()
    g2.graph["model_id"] = "m2"
    g2.add_node("x", id="x", type="DataObject", label="Data")

    text = fmt.render_corpus([simple_graph, g2])
    graphs = fmt.parse(text)
    assert len(graphs) == 2
    assert graphs[0].number_of_nodes() == 2
    assert graphs[1].number_of_nodes() == 1


# ── parse_patterns (CMiner extended format) ───────────────────────────────────

EXTENDED_GSPAN = """\
t # 0 model-001
v 0 BusinessRole
v 1 ApplicationService
e 0 1 Serving
s 3
f 0.75
info:
Some textual description
----------
t # 1 model-002
v 0 DataObject
s 1
f 0.25
"""


def test_parse_patterns_count(fmt):
    results = fmt.parse_patterns(EXTENDED_GSPAN)
    assert len(results) == 2


def test_parse_patterns_support(fmt):
    results = fmt.parse_patterns(EXTENDED_GSPAN)
    assert results[0].support == 3.0
    assert results[1].support == 1.0


def test_parse_patterns_frequency(fmt):
    results = fmt.parse_patterns(EXTENDED_GSPAN)
    assert results[0].frequency == 0.75
    assert results[1].frequency == 0.25


def test_parse_patterns_info(fmt):
    results = fmt.parse_patterns(EXTENDED_GSPAN)
    assert "Some textual description" in results[0].info


def test_parse_patterns_graph_content(fmt):
    results = fmt.parse_patterns(EXTENDED_GSPAN)
    assert results[0].graph.number_of_nodes() == 2
    assert results[0].graph.number_of_edges() == 1


# ── parse_file ────────────────────────────────────────────────────────────────

def test_parse_file(fmt, simple_graph, tmp_path):
    gspan_file = tmp_path / "test.gspan"
    gspan_file.write_text(fmt.render(simple_graph), encoding="utf-8")
    graphs = fmt.parse_file(str(gspan_file))
    assert len(graphs) == 1
    assert graphs[0].number_of_nodes() == 2


# ── Multi-label nodes ─────────────────────────────────────────────────────────

MULTI_LABEL_GSPAN = """\
t # 0 test
v 0 kind functional-complex
v 1 relator relator
v 2 kind collective
e 0 1 mediation
e 1 2 mediation
"""


def test_parse_multi_label_nodes(fmt):
    graphs = fmt.parse(MULTI_LABEL_GSPAN)
    assert len(graphs) == 1
    g = graphs[0]
    assert g.nodes[0]["labels"] == ["kind", "functional-complex"]
    assert g.nodes[1]["labels"] == ["relator", "relator"]
    assert g.nodes[2]["labels"] == ["kind", "collective"]
    assert g.nodes[0]["type"] == "kind"
    assert g.nodes[1]["type"] == "relator"


def test_render_multi_label_nodes(fmt):
    g = nx.MultiDiGraph()
    g.graph["model_id"] = "test"
    g.add_node(0, id="0", type="kind", label="kind", labels=["kind", "functional-complex"])
    g.add_node(1, id="1", type="relator", label="relator", labels=["relator", "relator"])
    g.add_edge(0, 1, type="mediation", label="mediation")

    text = fmt.render(g)
    assert "v 0 kind functional-complex" in text
    assert "v 1 relator relator" in text


def test_multi_label_roundtrip(fmt):
    graphs = fmt.parse(MULTI_LABEL_GSPAN)
    text = fmt.render(graphs[0])
    graphs2 = fmt.parse(text)
    assert graphs2[0].nodes[0]["labels"] == ["kind", "functional-complex"]
    assert graphs2[0].nodes[2]["labels"] == ["kind", "collective"]
