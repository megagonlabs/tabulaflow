from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pandas as pd

from tabulaflow.app.pane import CARD_ID_PREFIX, VIEW_KINDS, CardData, PaneCard
from tabulaflow.app.pane.cards import render_graph_data, render_map_data, render_result_data
from tabulaflow.core.types import GraphView, GraphViewEdge, GraphViewNode
from tabulaflow.toolhub.render_graph import materialize_graph_view, normalize_graph_spec


def _load_card_data(card: PaneCard, pane_dir: Path) -> CardData:
    return cast(CardData, json.loads((pane_dir / f"{card['id']}.data.json").read_text()))


def _load_card_data_strict(card: PaneCard, pane_dir: Path) -> CardData:
    text = (pane_dir / f"{card['id']}.data.json").read_text()
    return cast(CardData, json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token))))


def _assert_columns(value: object) -> None:
    assert isinstance(value, list)
    for column in value:
        assert isinstance(column, dict)
        assert isinstance(column.get("field"), str)
        assert isinstance(column.get("title"), str)
        assert column.get("role") in {"text", "number", "bool", "media"}


def _assert_dataset(value: object) -> None:
    assert isinstance(value, dict)
    rows = value.get("rows")
    assert isinstance(rows, list)
    assert all(isinstance(row, dict) for row in rows)
    if "columns" in value:
        _assert_columns(value["columns"])


def _assert_card_payload(card: PaneCard, data: CardData) -> None:
    assert card["id"].startswith(CARD_ID_PREFIX)
    assert set(card["views"]) <= set(VIEW_KINDS)

    if "data" in card["views"]:
        assert "dataset" in data
        assert "table" in data
        _assert_dataset(data["dataset"])
        _assert_columns(data["table"]["columns"])

    if "chart" in card["views"]:
        chart = data["chart"]
        assert isinstance(chart["spec"], dict)
        assert isinstance(chart["renderer"], str)
        assert isinstance(chart["wrapClass"], str)

    if "query" in card["views"]:
        query = data["query"]
        assert isinstance(query["code"], str)
        assert isinstance(query["lexer"], str)
        assert isinstance(query["language"], str)
        assert isinstance(query["html"], str)

    if "map" in card["views"]:
        map_data = data["map"]
        datasets = data["datasets"]
        assert map_data["provider"] == "maplibre"
        assert isinstance(map_data["layers"], list)
        assert isinstance(datasets, dict)
        assert datasets
        for dataset in datasets.values():
            _assert_dataset(dataset)
        for layer in map_data["layers"]:
            assert isinstance(layer, dict)
            source = layer.get("source")
            assert isinstance(source, str)
            assert source in datasets

    if "graph" in card["views"]:
        graph_data = data["graph"]
        assert graph_data["layout"] in {"force", "layered", "tree"}
        elements = graph_data["elements"]
        assert isinstance(elements["nodes"], list)
        assert isinstance(elements["edges"], list)
        for node in elements["nodes"]:
            node_data = node.get("data")
            assert isinstance(node_data, dict)
            assert isinstance(node_data.get("id"), str)
            assert isinstance(node_data.get("color"), str)
        for edge in elements["edges"]:
            edge_data = edge.get("data")
            assert isinstance(edge_data, dict)
            assert isinstance(edge_data.get("source"), str)
            assert isinstance(edge_data.get("target"), str)


def test_record_card_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["north", "south"], "revenue": [10, 20]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "region"}, "y": {"field": "revenue"}}}
    card = render_result_data(
        SimpleNamespace(
            df=df, chart_spec=spec, query="select region, revenue from sales", label="sales", query_lexer="sql"
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["chart", "data", "query"]
    _assert_card_payload(card, _load_card_data(card, tmp_path))


def test_record_card_with_attached_graph_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"path": ["Alice -> Matrix"]})
    graph = GraphView(
        nodes=[
            GraphViewNode(id="alice", label="Alice", group="Person"),
            GraphViewNode(id="matrix", label="The Matrix", group="Movie"),
        ],
        edges=[GraphViewEdge(id="acted_in", source="alice", target="matrix", label="ACTED_IN", directed=True)],
    )
    card = render_result_data(
        SimpleNamespace(
            df=df, chart_spec=None, graph=graph, query="MATCH p=()-->() RETURN p", label="paths", query_lexer="cypher"
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["graph", "data", "query"]
    _assert_card_payload(card, _load_card_data(card, tmp_path))


def test_map_card_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"city": ["San Francisco"], "lat": [37.7749], "lng": [-122.4194]})
    card = render_map_data(
        SimpleNamespace(
            map_id="MAP1",
            label="locations",
            map_spec={"layers": [{"type": "points", "source": "Q1", "lat": "lat", "lng": "lng", "label": "city"}]},
            sources={"Q1": df},
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["map"]
    _assert_card_payload(card, _load_card_data(card, tmp_path))


def test_graph_card_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"src": ["a"], "dst": ["b"], "rel": ["feeds"]})
    spec = {
        "layout": "layered",
        "nodes": [{"source_id": "Q1", "id": "src"}, {"source_id": "Q1", "id": "dst"}],
        "edges": [{"source_id": "Q1", "source": "src", "target": "dst", "label": "rel"}],
    }
    normalized = normalize_graph_spec(spec, {"Q1": df})
    card = render_graph_data(
        SimpleNamespace(
            graph_id="GRAPH1",
            label="lineage",
            graph=materialize_graph_view(normalized, {"Q1": df}),
            layout=normalized["layout"],
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["graph"]
    _assert_card_payload(card, _load_card_data(card, tmp_path))


def test_graph_card_omits_directed_flag_for_undirected_edges(tmp_path: Path) -> None:
    df = pd.DataFrame({"src": ["a"], "dst": ["b"]})
    spec = {
        "layout": "force",
        "nodes": [{"source_id": "Q1", "id": "src"}, {"source_id": "Q1", "id": "dst"}],
        "edges": [{"source_id": "Q1", "source": "src", "target": "dst", "directed": False}],
    }
    normalized = normalize_graph_spec(spec, {"Q1": df})
    card = render_graph_data(
        SimpleNamespace(
            graph_id="GRAPH1",
            label="network",
            graph=materialize_graph_view(normalized, {"Q1": df}),
            layout=normalized["layout"],
        ),
        tmp_path,
    )

    assert card is not None
    data = _load_card_data(card, tmp_path)
    edge_data = data["graph"]["elements"]["edges"][0]["data"]
    assert isinstance(edge_data, dict)
    assert "directed" not in edge_data


def test_graph_card_writes_strict_json_for_non_finite_values(tmp_path: Path) -> None:
    graph = GraphView(
        nodes=[
            GraphViewNode(id="director", label="Director", group="Director", properties={"rating": math.nan}),
            GraphViewNode(id="movie", label="Movie", group="Movie", properties={"score": math.inf}),
        ],
        edges=[
            GraphViewEdge(source="director", target="movie", label="DIRECTED", properties={"imdb_rating": math.nan})
        ],
    )
    card = render_graph_data(
        SimpleNamespace(graph_id="GRAPH1", label="graph", graph=graph, layout="force"),
        tmp_path,
    )

    assert card is not None
    text = (tmp_path / f"{card['id']}.data.json").read_text()
    assert "NaN" not in text
    assert "Infinity" not in text
    data = _load_card_data_strict(card, tmp_path)
    nodes = cast(list[dict[str, Any]], data["graph"]["elements"]["nodes"])
    edges = cast(list[dict[str, Any]], data["graph"]["elements"]["edges"])
    assert nodes[0]["data"]["properties"]["rating"] is None
    assert nodes[1]["data"]["properties"]["score"] is None
    assert edges[0]["data"]["properties"]["imdb_rating"] is None
