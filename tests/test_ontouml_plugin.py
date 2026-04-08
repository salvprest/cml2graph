"""
Tests for the OntoUML plugin.

Covers every fix to guard against regressions.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import networkx as nx
import pytest

from cml2graph.plugins.ontouml.plugin import OntoUMLPlugin
from cml2graph.plugins.ontouml.validator import validate_model
from cml2graph.core.language_schema import LanguagePlugin
from cml2graph.core.formats.gspan_fmt import GSpanFormat


# ── fixtures ─────────────────────────────────────────────────────

MINIMAL_MODEL = {
    "type": "Package",
    "id": "pkg1",
    "name": "TestModel",
    "contents": [
        {"type": "Class", "id": "c1", "name": "Person",
         "stereotype": "kind", "restrictedTo": ["functional-complex"]},
        {"type": "Class", "id": "c2", "name": "Organization",
         "stereotype": "kind", "restrictedTo": ["functional-complex"]},
        {"type": "Class", "id": "c3", "name": "Employment",
         "stereotype": "relator", "restrictedTo": ["relator"]},
        {"type": "Class", "id": "c4", "name": "Student",
         "stereotype": "role", "restrictedTo": ["functional-complex"]},
        {
            "type": "Relation", "id": "r1",
            "name": "involves", "stereotype": "mediation",
            "properties": [
                {"propertyType": {"id": "c3"}, "cardinality": "1"},
                {"propertyType": {"id": "c1"}, "cardinality": "1..*"},
            ],
        },
        {
            "type": "Relation", "id": "r2",
            "name": "", "stereotype": "mediation",
            "properties": [
                {"propertyType": {"id": "c3"}, "cardinality": "1"},
                {"propertyType": {"id": "c2"}, "cardinality": "1..*"},
            ],
        },
        {"type": "Generalization", "id": "g1",
         "general": {"id": "c1"}, "specific": {"id": "c4"}},
        {"type": "Generalization", "id": "g2",
         "general": {"id": "c1"}, "specific": {"id": "c3"}},
        {
            "type": "GeneralizationSet", "id": "gs1",
            "name": "PersonRoles", "isDisjoint": True, "isComplete": False,
            "generalizations": [{"id": "g1"}, {"id": "g2"}],
        },
    ],
}


def _write_model(data: dict) -> str:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, f, ensure_ascii=False)
    f.close()
    return f.name


# ── protocol ─────────────────────────────────────────────────────

def test_plugin_satisfies_protocol():
    assert isinstance(OntoUMLPlugin(), LanguagePlugin)


# ── parsing ──────────────────────────────────────────────────────

def test_parse_basic():
    path = _write_model(MINIMAL_MODEL)
    G = OntoUMLPlugin().parse(path)

    assert isinstance(G, nx.MultiDiGraph)
    assert "c1" in G
    assert G.nodes["c1"]["type"] == "kind"
    assert G.nodes["c1"]["label"] == "Person"

    edge_types = [d["type"] for _, _, d in G.edges(data=True)]
    assert edge_types.count("mediation") == 2
    assert edge_types.count("generalization") == 2
    Path(path).unlink()


def test_parse_error_on_bad_json():
    path = _write_model({"not": "a model"})
    with pytest.raises(ValueError):
        OntoUMLPlugin().parse(path)
    Path(path).unlink()


# ── FIX 1: genset_id on generalization edges ─────────────────────

def test_genset_ids_on_edges():
    path = _write_model(MINIMAL_MODEL)
    G = OntoUMLPlugin().parse(path)

    gen_edges = [
        d for _, _, d in G.edges(data=True)
        if d["type"] == "generalization"
    ]

    # Check that edges carry genset_ids (list, not singular genset_id)
    with_gsid = [e for e in gen_edges if e.get("genset_ids")]
    assert len(with_gsid) == 2, "both gens should carry genset_ids"

    # Both belong to gs1
    for edge in with_gsid:
        assert "gs1" in edge["genset_ids"]
        assert True in edge["genset_is_disjoint"]
        assert False in edge["genset_is_complete"]

    Path(path).unlink()


def test_genset_metadata_at_graph_level():
    path = _write_model(MINIMAL_MODEL)
    G = OntoUMLPlugin().parse(path)

    gs_list = G.graph.get("generalization_sets", [])
    assert len(gs_list) == 1
    assert gs_list[0]["id"] == "gs1"
    assert set(gs_list[0]["generalizations"]) == {"g1", "g2"}
    Path(path).unlink()

# Test multiple and dangling

def test_generalization_in_multiple_gensets():
    """A single generalization belonging to two GenSets."""
    model = {
        "type": "Package", "id": "pkg",
        "contents": [
            {"type": "Class", "id": "c1", "name": "Animal", "stereotype": "kind"},
            {"type": "Class", "id": "c2", "name": "Dog", "stereotype": "subkind"},
            {"type": "Class", "id": "c3", "name": "Cat", "stereotype": "subkind"},
            {"type": "Generalization", "id": "g1",
             "general": {"id": "c1"}, "specific": {"id": "c2"}},
            {"type": "Generalization", "id": "g2",
             "general": {"id": "c1"}, "specific": {"id": "c3"}},
            {
                "type": "GeneralizationSet", "id": "gs1",
                "name": "Pets", "isDisjoint": True, "isComplete": False,
                "generalizations": [{"id": "g1"}, {"id": "g2"}],
            },
            {
                "type": "GeneralizationSet", "id": "gs2",
                "name": "Domestic", "isDisjoint": False, "isComplete": True,
                "generalizations": [{"id": "g1"}],
            },
        ],
    }
    path = _write_model(model)
    G = OntoUMLPlugin().parse(path)

    # g1 (Dog→Animal) should belong to BOTH gs1 and gs2
    g1_edges = [
        d for u, v, k, d in G.edges(keys=True, data=True)
        if d.get("id") == "g1"
    ]
    assert len(g1_edges) == 1
    edge = g1_edges[0]

    assert set(edge["genset_ids"]) == {"gs1", "gs2"}
    assert len(edge["genset_is_disjoint"]) == 2
    assert len(edge["genset_is_complete"]) == 2

    # gs1 is disjoint=True, gs2 is disjoint=False
    # Order depends on genset_index iteration but both must be present
    assert True in edge["genset_is_disjoint"]
    assert False in edge["genset_is_disjoint"]

    # g2 (Cat→Animal) belongs to only gs1
    g2_edges = [
        d for u, v, k, d in G.edges(keys=True, data=True)
        if d.get("id") == "g2"
    ]
    assert len(g2_edges) == 1
    assert g2_edges[0]["genset_ids"] == ["gs1"]
    assert g2_edges[0]["genset_is_disjoint"] == [True]
    assert g2_edges[0]["genset_is_complete"] == [False]

    # PlantUML should show both gensets on g1
    text = OntoUMLPlugin().render(G, "plantuml")
    assert "Pets" in text
    assert "Domestic" in text
    assert "{disjoint}" in text
    assert "{complete}" in text

    # JSON round-trip should preserve both gensets
    json_text = OntoUMLPlugin().render(G, "json")
    rendered = json.loads(json_text)
    gs_elems = [
        c for c in rendered["contents"]
        if c["type"] == "GeneralizationSet"
    ]
    assert len(gs_elems) == 2

    Path(path).unlink()

def test_dangling_reference_skips_edge():
    """Edge referencing non-existent class should be skipped, not create a fake node."""
    model = {
        "type": "Package", "id": "pkg",
        "contents": [
            {"type": "Class", "id": "c1", "name": "Person", "stereotype": "kind"},
            {
                "type": "Relation", "id": "r1",
                "name": "", "stereotype": "mediation",
                "properties": [
                    {"propertyType": {"id": "c1"}, "cardinality": "1"},
                    {"propertyType": {"id": "c_missing"}, "cardinality": "*"},
                ],
            },
        ],
    }
    path = _write_model(model)
    G = OntoUMLPlugin().parse(path)

    # Only c1 should exist, no fake c_missing node
    assert "c1" in G
    assert "c_missing" not in G

    # No edges (the relation was skipped)
    assert G.number_of_edges() == 0

    Path(path).unlink()

# ── FIX 2: JSON round-trip preserves GeneralizationSets ──────────

def test_json_roundtrip_gensets():
    path = _write_model(MINIMAL_MODEL)
    plugin = OntoUMLPlugin()
    G = plugin.parse(path)
    json_text = plugin.render(G, "json")
    rendered = json.loads(json_text)

    types_found = {c["type"] for c in rendered["contents"]}
    assert "GeneralizationSet" in types_found

    gs_elems = [c for c in rendered["contents"]
                if c["type"] == "GeneralizationSet"]
    assert len(gs_elems) == 1
    assert gs_elems[0]["isDisjoint"] is True
    assert set(
        g["id"] for g in gs_elems[0]["generalizations"]
    ) == {"g1", "g2"}
    Path(path).unlink()


# ── FIX 4: by_nature with empty strings ──────────────────────────

def test_by_nature_empty_string_no_match():
    path = _write_model(MINIMAL_MODEL)
    G = OntoUMLPlugin().parse(path)

    # Add a node with empty nature
    G.add_node("orphan", id="orphan", label="Ghost",
               type="class", nature="", stereotype="class", category="")

    filters = OntoUMLPlugin().get_filters()
    sub = filters["by_nature"](G, "functional-complex")
    assert "orphan" not in sub
    Path(path).unlink()


# ── FIX 5: _safe_alias ──────────────────────────────────────────

def test_plantuml_alias_starts_with_letter():
    from cml2graph.plugins.ontouml.renderer import _safe_alias

    # UUID-like, starts with digit after stripping
    alias = _safe_alias("550e8400-e29b-41d4")
    assert alias[0].isalpha(), f"alias starts with non-letter: {alias}"

    # All-numeric
    alias2 = _safe_alias("12345")
    assert alias2[0].isalpha()

    # Empty
    alias3 = _safe_alias("")
    assert len(alias3) > 0 and alias3[0].isalpha()


# ── FIX 6: normalize_types ──────────────────────────────────────

def test_normalize_types():
    path = _write_model(MINIMAL_MODEL)
    plugin = OntoUMLPlugin()
    G = plugin.parse(path)
    filters = plugin.get_filters()

    H = filters["normalize_types"](G)
    for n, d in H.nodes(data=True):
        assert d["type"] in ("class", "generalization"), \
            f"node {n} has unexpected type {d['type']}"

    edge_types = {d["type"] for _, _, d in H.edges(data=True)}
    # mediation edges should now be "relation", generalizations stay
    assert "relation" in edge_types or "generalization" in edge_types
    Path(path).unlink()


# ── validator ────────────────────────────────────────────────────

def test_validator_catches_missing_id():
    issues = validate_model({"contents": [{"type": "Class", "name": "X"}]})
    assert any(i.severity == "error" for i in issues)


def test_validator_warns_unknown_stereotype():
    issues = validate_model(
        {"contents": [{"type": "Class", "id": "x", "name": "X",
                        "stereotype": "foobar"}]}
    )
    assert any("foobar" in i.message for i in issues
               if i.severity == "warning")


# ── renderers ────────────────────────────────────────────────────

def test_render_plantuml():
    path = _write_model(MINIMAL_MODEL)
    text = OntoUMLPlugin().render(
        OntoUMLPlugin().parse(path), "plantuml"
    )
    assert "@startuml" in text
    assert "Person" in text
    assert "<<kind>>" in text
    assert "-up-|>" in text
    assert "{disjoint}" in text
    assert "@enduml" in text
    Path(path).unlink()


def test_render_gspan():
    path = _write_model(MINIMAL_MODEL)
    text = OntoUMLPlugin().render(
        OntoUMLPlugin().parse(path), "gspan"
    )
    assert text.startswith("t #")
    assert "v " in text
    assert "e " in text
    Path(path).unlink()


# ── filters ──────────────────────────────────────────────────────

def test_by_stereotype():
    path = _write_model(MINIMAL_MODEL)
    G = OntoUMLPlugin().parse(path)
    sub = OntoUMLPlugin().get_filters()["by_stereotype"](G, "kind")
    assert all(G.nodes[n]["stereotype"] == "kind" for n in sub)
    assert len(sub) == 2
    Path(path).unlink()


def test_without_orphans():
    path = _write_model(MINIMAL_MODEL)
    G = OntoUMLPlugin().parse(path)
    sub = OntoUMLPlugin().get_filters()["without_orphans"](G)
    for n in sub:
        assert sub.degree(n) > 0
    Path(path).unlink()


# ── prompts metadata ──────────────────────────────────────────────

def test_filter_tools_keys_match_get_filters():
    """Every key in FILTER_TOOLS must correspond to a real filter function."""
    from cml2graph.plugins.ontouml.prompts import FILTER_TOOLS
    filters = OntoUMLPlugin().get_filters()
    for name in FILTER_TOOLS:
        assert name in filters, (
            f"FILTER_TOOLS has '{name}' but get_filters() does not"
        )


def test_filter_tools_param_names_match_signatures():
    """Param names in FILTER_TOOLS must match the filter function signatures
    so that **args unpacking works at call time."""
    import inspect
    from cml2graph.plugins.ontouml.prompts import FILTER_TOOLS
    filters = OntoUMLPlugin().get_filters()
    for filter_name, meta in FILTER_TOOLS.items():
        sig_params = set(inspect.signature(filters[filter_name]).parameters) - {"graph"}
        meta_params = set(meta.get("params", {}).keys())
        assert meta_params <= sig_params, (
            f"Filter '{filter_name}': metadata params {meta_params} "
            f"not a subset of signature params {sig_params}"
        )


def test_filter_tools_params_have_type_field():
    """All params with an enum should carry a 'type' field for schema generation."""
    from cml2graph.plugins.ontouml.prompts import FILTER_TOOLS
    for filter_name, meta in FILTER_TOOLS.items():
        for param_name, param_meta in meta.get("params", {}).items():
            if "enum" in param_meta:
                assert "type" in param_meta, (
                    f"Filter '{filter_name}', param '{param_name}' "
                    f"has 'enum' but no 'type'"
                )


def test_filter_tools_enums_are_non_empty():
    """Every enum list in FILTER_TOOLS must be non-empty."""
    from cml2graph.plugins.ontouml.prompts import FILTER_TOOLS
    for filter_name, meta in FILTER_TOOLS.items():
        for param_name, param_meta in meta.get("params", {}).items():
            if "enum" in param_meta:
                assert len(param_meta["enum"]) > 0, (
                    f"Filter '{filter_name}', param '{param_name}' has empty enum"
                )


# ── enrich_pattern ────────────────────────────────────────────────────────────

def test_enrich_skeleton_gets_stereotype_and_category():
    gspan_text = "t # 0\nv 0 kind\nv 1 relator\ne 0 1 mediation"
    graphs = GSpanFormat().parse(gspan_text)

    plugin = OntoUMLPlugin()
    enriched = plugin.enrich_pattern(graphs[0])

    node_0 = enriched.nodes[0]
    node_1 = enriched.nodes[1]

    assert node_0["stereotype"] == "kind"
    assert node_0["category"] == "Substantial"
    assert node_1["stereotype"] == "relator"
    assert node_1["category"] == "Moment"


def test_enrich_skeleton_unique_labels_no_suffix():
    gspan_text = "t # 0\nv 0 kind\nv 1 relator\ne 0 1 mediation"
    graphs = GSpanFormat().parse(gspan_text)

    plugin = OntoUMLPlugin()
    enriched = plugin.enrich_pattern(graphs[0])

    assert enriched.nodes[0]["label"] == "kind"
    assert enriched.nodes[1]["label"] == "relator"


def test_enrich_duplicate_types_get_numbered():
    gspan_text = "t # 0\nv 0 kind\nv 1 kind\ne 0 1 characterization"
    graphs = GSpanFormat().parse(gspan_text)

    plugin = OntoUMLPlugin()
    enriched = plugin.enrich_pattern(graphs[0])

    labels = {enriched.nodes[n]["label"] for n in enriched.nodes}
    assert labels == {"kind_0", "kind_1"}


def test_enrich_unknown_type_gets_empty_category():
    gspan_text = "t # 0\nv 0 UnknownStereotype\ne 0 0 mediation"
    graphs = GSpanFormat().parse(gspan_text)

    plugin = OntoUMLPlugin()
    enriched = plugin.enrich_pattern(graphs[0])

    assert enriched.nodes[0]["category"] == ""


def test_enrich_edge_label_set_from_type():
    gspan_text = "t # 0\nv 0 kind\nv 1 relator\ne 0 1 mediation"
    graphs = GSpanFormat().parse(gspan_text)

    plugin = OntoUMLPlugin()
    enriched = plugin.enrich_pattern(graphs[0])

    edge_data = next(iter(enriched.edges(data=True)))[2]
    assert edge_data["label"] == "mediation"


def test_enrich_non_skeleton_unchanged():
    path = _write_model(MINIMAL_MODEL)
    plugin = OntoUMLPlugin()
    graph = plugin.parse(path)
    original_labels = {d["label"] for _, d in graph.nodes(data=True)}

    enriched = plugin.enrich_pattern(graph)
    new_labels = {d["label"] for _, d in enriched.nodes(data=True)}

    assert original_labels == new_labels