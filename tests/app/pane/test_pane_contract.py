from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
import pytest

from tabulaflow.app.pane.contract import CARD_ID_PREFIX, VIEW_KINDS, CardData, PaneCard
from tabulaflow.app.pane.cards import (
    GraphCardInput,
    MapCardInput,
    ResultCardInput,
    build_query_data,
    render_graph_data,
    render_map_data,
    render_resolved_output,
    render_result_data,
)
from tabulaflow.app.pane.graphs import build_graph_result_data
from tabulaflow.core import GraphResult, GraphResultEdge, GraphResultNode
from tabulaflow.output.graphs import materialize_graph_result, normalize_graph_spec
from tabulaflow.output.resolver import ResolvedOutput, ResolvedTableArtifact, UnavailableArtifact
from tabulaflow.output.store import ResultMetadata, MaterializedResult


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
    _assert_columns(value.get("columns"))


def _assert_card_payload(card: PaneCard, data: CardData) -> None:
    assert card["id"].startswith(CARD_ID_PREFIX)
    assert card["artifact_id"]
    assert set(card["views"]) <= set(VIEW_KINDS)

    if "data" in card["views"]:
        assert "dataset" in data
        assert "table" in data
        _assert_dataset(data["dataset"])

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
        for edge in elements["edges"]:
            edge_data = edge.get("data")
            assert isinstance(edge_data, dict)
            assert isinstance(edge_data.get("source"), str)
            assert isinstance(edge_data.get("target"), str)


def test_result_card_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["north", "south"], "revenue": [10, 20]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "region"}, "y": {"field": "revenue"}}}
    card = render_result_data(
        ResultCardInput(
            df=df, label="sales", chart_spec=spec, query="select region, revenue from sales", query_lexer="sql"
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["chart", "data", "query"]
    _assert_card_payload(card, _load_card_data(card, tmp_path))


def test_result_card_with_attached_graph_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"path": ["Alice -> Matrix"]})
    graph = GraphResult(
        nodes=[
            GraphResultNode(id="alice", label="Alice", group="Person"),
            GraphResultNode(id="matrix", label="The Matrix", group="Movie"),
        ],
        edges=[GraphResultEdge(id="acted_in", source="alice", target="matrix", label="ACTED_IN", directed=True)],
    )
    card = render_result_data(
        ResultCardInput(df=df, label="paths", graph=graph, query="MATCH p=()-->() RETURN p", query_lexer="cypher"),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["graph", "data", "query"]
    _assert_card_payload(card, _load_card_data(card, tmp_path))


def test_map_card_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"city": ["San Francisco"], "lat": [37.7749], "lng": [-122.4194]})
    card = render_map_data(
        MapCardInput(
            label="locations",
            spec={"layers": [{"type": "points", "source_id": "Q1", "lat": "lat", "lng": "lng", "label": "city"}]},
            sources={"Q1": df},
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["map"]
    data = _load_card_data(card, tmp_path)
    _assert_card_payload(card, data)
    assert data["map"]["layers"] == [{"type": "points", "source": "Q1", "lat": "c1", "lng": "c2", "label": "c0"}]
    assert data["datasets"]["Q1"]["rows"] == [{"c0": "San Francisco", "c1": 37.7749, "c2": -122.4194}]


def test_graph_card_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"src": ["a"], "dst": ["b"], "rel": ["feeds"]})
    spec = {
        "layout": "layered",
        "nodes": [{"source_id": "Q1", "id": "src"}, {"source_id": "Q1", "id": "dst"}],
        "edges": [{"source_id": "Q1", "source": "src", "target": "dst", "label": "rel"}],
    }
    normalized = normalize_graph_spec(spec, {"Q1": df})
    card = render_graph_data(
        GraphCardInput(
            label="lineage",
            graph=materialize_graph_result(normalized, {"Q1": df}),
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
        GraphCardInput(
            label="network",
            graph=materialize_graph_result(normalized, {"Q1": df}),
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
    graph = GraphResult(
        nodes=[
            GraphResultNode(id="director", label="Director", group="Director", properties={"rating": math.nan}),
            GraphResultNode(id="movie", label="Movie", group="Movie", properties={"score": math.inf}),
        ],
        edges=[
            GraphResultEdge(source="director", target="movie", label="DIRECTED", properties={"imdb_rating": math.nan})
        ],
    )
    card = render_graph_data(
        GraphCardInput(label="graph", graph=graph, layout="force"),
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


def test_empty_chart_result_keeps_chart_and_data_views(tmp_path: Path) -> None:
    df = pd.DataFrame({"customer": pd.Series(dtype="object"), "value": pd.Series(dtype="int64")})
    spec = {"mark": "bar", "encoding": {"x": {"field": "customer"}, "y": {"field": "value"}}}
    card = render_result_data(ResultCardInput(df=df, label="empty chart", chart_spec=spec), tmp_path)

    assert card is not None
    assert card["views"] == ["chart", "data"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["chart"]["spec"]["mark"] == "bar"
    assert payload["table"]["meta"] == "0 rows · 2 columns"


def _map_card(
    map_spec: dict[str, object],
    sources: dict[str, pd.DataFrame],
    tmp_path: Path,
    *,
    label: str = "map",
) -> PaneCard:
    card = render_map_data(MapCardInput(label=label, spec=map_spec, sources=sources), tmp_path)
    assert card is not None
    assert card["id"].startswith(CARD_ID_PREFIX)
    return card


def test_map_card_preserves_blank_coordinate_strings_for_map_renderer(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["Missing", "San Francisco"],
            "latitude": ["", "37.7749"],
            "longitude": ["", "-122.4194"],
        }
    )
    card = _map_card(
        {"layers": [{"type": "points", "source_id": "Q1", "lat": "latitude", "lng": "longitude", "label": "city"}]},
        {"Q1": df},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["datasets"]["Q1"]["rows"][0]["c1"] == ""
    assert payload["datasets"]["Q1"]["rows"][0]["c2"] == ""


def test_map_card_preserves_size_domain_and_circle_marker(tmp_path: Path) -> None:
    df = pd.DataFrame({"lat": [1.0], "lng": [2.0], "value": [50]})
    card = _map_card(
        {
            "layers": [
                {
                    "type": "points",
                    "source_id": "Q1",
                    "lat": "lat",
                    "lng": "lng",
                    "size": {"field": "value", "domain": [0, 100]},
                    "marker": {"type": "circle"},
                }
            ]
        },
        {"Q1": df},
        tmp_path,
    )

    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["size"] == {"field": "c2", "domain": [0, 100]}
    assert payload["map"]["layers"][0]["marker"] == {"type": "circle"}


def test_map_card_writes_layered_single_source_payload(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["San Francisco"],
            "latitude": [37.7749],
            "longitude": [-122.4194],
            "region": ["Bay Area"],
            "category": ["urban"],
            "boundary_geojson": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-122.52, 37.70],
                                [-122.35, 37.70],
                                [-122.35, 37.84],
                                [-122.52, 37.84],
                                [-122.52, 37.70],
                            ]
                        ],
                    },
                    "properties": {"kind": "region"},
                }
            ],
        }
    )
    card = _map_card(
        {
            "layers": [
                {
                    "type": "geojson",
                    "source_id": "Q1",
                    "geojson": "boundary_geojson",
                    "label": "region",
                    "tooltip": ["category"],
                    "color": {"field": "region"},
                },
                {
                    "type": "points",
                    "source_id": "Q1",
                    "lat": "latitude",
                    "lng": "longitude",
                    "label": "city",
                    "tooltip": ["category"],
                },
            ]
        },
        {"Q1": df},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["type"] == "geojson"
    assert payload["map"]["layers"][0]["source"] == "Q1"
    assert payload["map"]["layers"][0]["geojson"] == "c5"
    assert payload["map"]["layers"][0]["label"] == "c3"
    assert payload["map"]["layers"][0]["tooltip"] == ["c4"]
    assert payload["map"]["layers"][0]["color"] == {"field": "c3"}
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "source": "Q1",
        "lat": "c1",
        "lng": "c2",
        "label": "c0",
        "tooltip": ["c4"],
    }


def test_map_card_writes_multi_source_datasets(tmp_path: Path) -> None:
    boundaries = pd.DataFrame(
        {
            "area": ["Bay Area"],
            "boundary_geojson": [{"type": "Point", "coordinates": [-122.4, 37.7]}],
        }
    )
    points = pd.DataFrame({"city": ["San Francisco"], "latitude": [37.7749], "longitude": [-122.4194]})
    card = _map_card(
        {
            "layers": [
                {"type": "geojson", "source_id": "Q1", "geojson": "boundary_geojson", "label": "area"},
                {"type": "points", "source_id": "Q2", "lat": "latitude", "lng": "longitude", "label": "city"},
            ]
        },
        {"Q1": boundaries, "Q2": points},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    # Each layer reads from its own source's compact field names.
    assert payload["map"]["layers"][0] == {"type": "geojson", "source": "Q1", "geojson": "c1", "label": "c0"}
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "source": "Q2",
        "lat": "c1",
        "lng": "c2",
        "label": "c0",
    }
    assert set(payload["datasets"]) == {"Q1", "Q2"}
    assert payload["datasets"]["Q2"]["rows"][0]["c1"] == 37.7749


def test_map_card_writes_inline_point_layer(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "route_geojson": [
                {
                    "type": "LineString",
                    "coordinates": [[-122.42, 37.77], [-122.27, 37.80]],
                }
            ],
            "route_name": ["Route"],
        }
    )
    card = _map_card(
        {
            "layers": [
                {"type": "geojson", "source_id": "Q1", "geojson": "route_geojson", "label": "route_name"},
                {
                    "type": "points",
                    "points": [{"lat": 37.8044, "lng": -122.2712, "label": "Destination", "kind": "destination"}],
                    "label": "label",
                    "tooltip": ["kind"],
                },
            ]
        },
        {"Q1": df},
        tmp_path,
        label="route",
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["geojson"] == "c0"
    assert payload["map"]["layers"][0]["label"] == "c1"
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "points": [{"lat": 37.8044, "lng": -122.2712, "label": "Destination", "kind": "destination"}],
        "label": "label",
        "tooltip": ["kind"],
    }


def test_graph_tooltips_preserve_nested_values() -> None:
    spec = {
        "nodes": [
            {
                "data": [
                    {"id": "a", "label": "Alice", "tags": ["lead"], "profile": {"city": "Oakland"}},
                    {"id": "b", "label": "Bob"},
                ],
                "id": "id",
                "label": "label",
                "tooltip": True,
            }
        ],
        "edges": [
            {
                "data": [
                    {
                        "src": "a",
                        "dst": "b",
                        "rel": "knows",
                        "roles": ["mentor", "reviewer"],
                        "metadata": {"since": 2024},
                    }
                ],
                "source": "src",
                "target": "dst",
                "label": "rel",
                "tooltip": True,
            }
        ],
    }
    normalized = normalize_graph_spec(spec, {})
    payload = build_graph_result_data(materialize_graph_result(normalized, {}))
    assert payload is not None
    # Element dicts hold ``object`` values; the test asserts on their nested shape.
    nodes = cast("list[dict[str, Any]]", payload["graph"]["elements"]["nodes"])
    edges = cast("list[dict[str, Any]]", payload["graph"]["elements"]["edges"])
    alice = next(node["data"] for node in nodes if node["data"]["id"] == "a")
    assert alice["properties"]["tags"] == ["lead"]
    assert alice["properties"]["profile"] == {"city": "Oakland"}
    assert edges[0]["data"]["properties"]["roles"] == ["mentor", "reviewer"]
    assert edges[0]["data"]["properties"]["metadata"] == {"since": 2024}


def test_graph_constant_group_colors_and_edge_label() -> None:
    spec = {
        "nodes": [
            {"data": [{"id": "a"}], "id": "id", "group": {"value": "Customer"}},
            {"data": [{"id": "p"}], "id": "id", "group": {"value": "Product"}},
        ],
        "edges": [
            {
                "data": [{"src": "a", "dst": "p"}],
                "source": "src",
                "target": "dst",
                "label": {"value": "PURCHASED"},
            }
        ],
    }
    normalized = normalize_graph_spec(spec, {})
    payload = build_graph_result_data(materialize_graph_result(normalized, {}))
    assert payload is not None
    nodes = cast("list[dict[str, Any]]", payload["graph"]["elements"]["nodes"])
    edges = cast("list[dict[str, Any]]", payload["graph"]["elements"]["edges"])
    by_id = {node["data"]["id"]: node["data"] for node in nodes}
    assert by_id["a"]["group"] == "Customer"
    assert by_id["p"]["group"] == "Product"
    assert edges[0]["data"]["label"] == "PURCHASED"


def test_graph_explicit_group_domain_controls_colors() -> None:
    graph = GraphResult(
        nodes=[GraphResultNode(id="customer", group="Customer"), GraphResultNode(id="product", group="Product")],
        edges=[],
    )

    payload = build_graph_result_data(graph, ["Product", "Customer"])

    assert payload is not None
    assert payload["graph"]["groupDomain"] == ["Product", "Customer"]
    nodes = cast("list[dict[str, Any]]", payload["graph"]["elements"]["nodes"])
    assert all("color" not in node["data"] for node in nodes)


def test_empty_graph_builds_a_normal_graph_payload() -> None:
    payload = build_graph_result_data(GraphResult(nodes=[], edges=[]))

    assert payload is not None
    assert payload["graph"]["elements"] == {"nodes": [], "edges": []}


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("not_applicable", "Only applies to revenue"),
        ("error", "boom"),
        ("no_result", "No result set"),
    ],
)
async def test_unavailable_artifact_renders_message_view(
    status: Literal["error", "not_applicable", "no_result"],
    reason: str,
    tmp_path: Path,
) -> None:
    resolved = ResolvedOutput(
        selection={},
        artifacts=[UnavailableArtifact(artifact_id="S1", label="detail", reason=reason, status=status)],
    )

    cards = await render_resolved_output(resolved, tmp_path)

    assert cards == [{"id": cards[0]["id"], "artifact_id": "S1", "label": "detail", "views": ["message"]}]
    payload = json.loads((tmp_path / f"{cards[0]['id']}.data.json").read_text())
    assert payload == {"message": {"status": status, "text": reason}}


async def test_pane_preparation_failure_renders_safe_error_card(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import tabulaflow.app.pane.cards as pane_cards

    artifact = ResolvedTableArtifact(
        artifact_id="S1",
        source_id="S1",
        label="orders",
        result=MaterializedResult(
            metadata=ResultMetadata(
                id="R1",
                connector_alias="workspace",
                query="SELECT * FROM orders",
                query_language="duckdb",
            ),
            df=pd.DataFrame({"id": [1]}),
        ),
    )

    def fail_render(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("internal detail")

    monkeypatch.setattr(pane_cards, "render_result_data", fail_render)

    cards = await render_resolved_output(ResolvedOutput(selection={}, artifacts=[artifact]), tmp_path)

    assert cards == [{"id": cards[0]["id"], "artifact_id": "S1", "label": "orders", "views": ["message"]}]
    payload = json.loads((tmp_path / f"{cards[0]['id']}.data.json").read_text())
    assert payload == {"message": {"status": "error", "text": "Could not prepare this artifact for display."}}
    assert "preparing pane card for artifact S1 failed" in caplog.text
    assert caplog.records[-1].levelname == "WARNING"
    assert "internal detail" not in payload["message"]["text"]


def test_query_payload_contains_language_and_highlighted_html() -> None:
    payload = build_query_data('print("Hello, world!")', lexer="python")

    query = payload["query"]
    assert isinstance(query, dict)
    assert query["code"] == 'print("Hello, world!")'
    assert query["lexer"] == "python"
    assert query["language"] == "Python"
    assert "print" in str(query["html"])


def test_query_payload_normalizes_sql_dialects_and_reports_fallback_lexer() -> None:
    snowflake = build_query_data("select 1", lexer="snowflake")["query"]
    unknown = build_query_data("select 1", lexer="not-a-real-lexer")["query"]
    cypher = build_query_data("MATCH (n) RETURN n", lexer="cypher")["query"]

    assert snowflake["lexer"] == "sql"
    assert snowflake["language"] == "SQL"
    assert unknown["lexer"] == "sql"
    assert unknown["language"] == "SQL"
    assert cypher["lexer"] == "cypher"
