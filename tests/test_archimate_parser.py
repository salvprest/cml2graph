"""Tests for ArchiMate parser and validator."""
import json
import pytest
from pathlib import Path

import networkx as nx

from cml2graph.plugins.archimate.parser import parse
from cml2graph.plugins.archimate.validator import validate_model

FIXTURE = Path(__file__).parent / "fixtures" / "simple_model.json"


# ── parse() happy path ────────────────────────────────────────────────────────

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
    # r1: e1 -> e3, Serving
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


# ── validate_model() ──────────────────────────────────────────────────────────

def test_validate_clean_model():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    issues = validate_model(data)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_validate_missing_both_keys():
    issues = validate_model({})
    severities = {i.severity for i in issues}
    assert "error" in severities


def test_validate_unknown_element_type_warning():
    data = {
        "elements": [{"id": "x1", "type": "Unicorn"}],
        "relationships": [],
    }
    issues = validate_model(data)
    warnings = [i for i in issues if i.severity == "warning"]
    assert any("Unknown element type" in i.message for i in warnings)


def test_validate_dangling_relationship():
    data = {
        "elements": [{"id": "e1", "type": "BusinessRole"}],
        "relationships": [
            {"id": "r1", "type": "Serving", "sourceId": "e1", "targetId": "GHOST"}
        ],
    }
    issues = validate_model(data)
    errors = [i for i in issues if i.severity == "error"]
    assert any("GHOST" in i.message for i in errors)


def test_validate_duplicate_element_id_warning():
    data = {
        "elements": [
            {"id": "e1", "type": "BusinessRole"},
            {"id": "e1", "type": "BusinessActor"},
        ],
        "relationships": [],
    }
    issues = validate_model(data)
    warnings = [i for i in issues if i.severity == "warning"]
    assert any("Duplicate" in i.message for i in warnings)
