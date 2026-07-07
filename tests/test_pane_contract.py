from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pandas as pd

from tabulaflow.app.pane import CARD_ID_PREFIX, VIEW_KINDS, CardData, PaneCard
from tabulaflow.app.pane.cards import render_map_data, render_record_data


def _load_card_data(card: PaneCard, pane_dir: Path) -> CardData:
    return cast(CardData, json.loads((pane_dir / f"{card['id']}.data.json").read_text()))


def _assert_columns(value: object) -> None:
    assert isinstance(value, list)
    for column in value:
        assert isinstance(column, dict)
        assert isinstance(column.get("field"), str)
        assert isinstance(column.get("title"), str)


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
        assert isinstance(query["sql"], str)
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


def test_record_card_payload_matches_contract(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["north", "south"], "revenue": [10, 20]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "region"}, "y": {"field": "revenue"}}}
    card = render_record_data(
        SimpleNamespace(df=df, chart_spec=spec, query="select region, revenue from sales", label="sales", query_lexer="sql"),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["chart", "data", "query"]
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
