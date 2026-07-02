"""Tests for the declarative map tool."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub.query_history import QueryHistory
from tabulaflow.toolhub.render_map import MAP_RENDER_MAX_ROWS, RenderMapTool, normalize_map_spec


async def _history_with(df: pd.DataFrame) -> QueryHistory:
    history = QueryHistory()
    await history.add("db", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=df)))
    return history


class TestNormalizeMapSpec:
    def test_points_layer_resolves_fields_case_insensitively(self) -> None:
        df = pd.DataFrame({"Lat": [37.7], "Lng": [-122.4], "Name": ["SF"]})
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng", "label": "name"}]}
        assert normalize_map_spec(df, spec) == {
            "layers": [{"type": "points", "lat": "Lat", "lng": "Lng", "label": "Name"}]
        }

    def test_points_layer_allows_mixed_missing_coordinates(self) -> None:
        df = pd.DataFrame(
            {
                "lat": [None, 37.7, 999],
                "lng": [-122.4, -122.4, -122.4],
                "name": ["missing", "valid", "invalid"],
            }
        )
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng", "label": "name"}]}
        assert normalize_map_spec(df, spec) == spec

    def test_points_layer_accepts_inline_points(self) -> None:
        df = pd.DataFrame({"route": ["r1"]})
        spec = {
            "layers": [
                {
                    "type": "points",
                    "points": [{"lat": 37.7, "lng": -122.4, "label": "Destination", "kind": "destination"}],
                    "label": "label",
                    "tooltip": ["label", "kind"],
                    "color": {"field": "kind", "domain": ["destination"]},
                    "marker": {"type": "pin"},
                }
            ]
        }
        assert normalize_map_spec(df, spec) == spec

    def test_inline_points_are_mutually_exclusive_with_column_points(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4]})
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng", "points": [{"lat": 37.7, "lng": -122.4}]}]}

        try:
            normalize_map_spec(df, spec)
        except ValueError as exc:
            assert "either points or lat/lng columns" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("mixed points modes should be rejected")

    def test_inline_points_validate_coordinates_and_properties(self) -> None:
        df = pd.DataFrame({"route": ["r1"]})
        cases = [
            {"layers": [{"type": "points", "points": [{"lat": None, "lng": -122.4}]}]},
            {"layers": [{"type": "points", "points": [{"lat": 999, "lng": -122.4}]}]},
            {"layers": [{"type": "points", "points": [{"lat": 37.7, "lng": -122.4, "meta": {"x": 1}}]}]},
            {"layers": [{"type": "points", "points": [{"lat": 37.7, "lng": -122.4}], "label": "missing"}]},
        ]

        for spec in cases:
            try:
                normalize_map_spec(df, spec)
            except ValueError:
                pass
            else:  # pragma: no cover - defensive
                raise AssertionError(f"invalid inline points should be rejected: {spec}")

    def test_geojson_layer_accepts_column(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [
                    {
                        "type": "Point",
                        "coordinates": [-122.4, 37.7],
                    }
                ],
                "name": ["SF"],
            }
        )
        spec = {"layers": [{"type": "geojson", "geojson": "geom", "tooltip": ["name"]}]}
        assert normalize_map_spec(df, spec) == {"layers": [{"type": "geojson", "geojson": "geom", "tooltip": ["name"]}]}

    def test_custom_basemap_is_rejected(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4]})
        spec = {
            "basemap": {"type": "tile", "tileUrl": "https://example.com/{z}/{x}/{y}.png"},
            "layers": [{"type": "points", "lat": "lat", "lng": "lng"}],
        }
        try:
            normalize_map_spec(df, spec)
        except ValueError as exc:
            assert "unsupported map_spec field" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("basemap should be rejected")

    def test_raw_styling_fields_are_rejected(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}],
                "status": ["open"],
                "value": [10],
            }
        )
        cases = [
            {"layers": [{"type": "geojson", "geojson": "geom", "style": {"weight": 1}}]},
            {"layers": [{"type": "geojson", "geojson": "geom", "color": "#3eb489"}]},
            {
                "layers": [
                    {
                        "type": "geojson",
                        "geojson": "geom",
                        "color": {"field": "status", "range": ["#3eb489"]},
                    }
                ]
            },
            {"layers": [{"type": "points", "lat": "value", "lng": "value", "size": 12}]},
            {
                "layers": [
                    {"type": "points", "lat": "value", "lng": "value", "size": {"field": "value", "range": [5, 18]}}
                ]
            },
        ]

        for spec in cases:
            try:
                normalize_map_spec(df, spec)
            except ValueError:
                pass
            else:  # pragma: no cover - defensive
                raise AssertionError(f"raw styling should be rejected: {spec}")

    def test_semantic_color_and_size_encodings_are_kept(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "status": ["open"], "value": [10]})
        spec = {
            "layers": [
                {
                    "type": "points",
                    "lat": "lat",
                    "lng": "lng",
                    "color": {"field": "status", "domain": ["open", "closed"]},
                    "size": {"field": "value"},
                }
            ]
        }
        assert normalize_map_spec(df, spec) == spec

    def test_legend_is_not_agent_facing_map_spec(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "status": ["open"]})
        spec = {"legend": True, "layers": [{"type": "points", "lat": "lat", "lng": "lng", "color": {"field": "status"}}]}
        with pytest.raises(ValueError, match="unsupported map_spec field"):
            normalize_map_spec(df, spec)


class TestRenderMapTool:
    async def test_record_id_required(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(history=history)(record_id="", map_spec=json.dumps(spec))
        assert "record_id must be a non-empty string" in msg

    async def test_points_map_attaches(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4], "name": ["SF"]}))
        spec = {"title": "Cities", "layers": [{"type": "points", "lat": "lat", "lng": "lng", "label": "name"}]}
        msg = await RenderMapTool(history=history)(record_id="Q1", map_spec=json.dumps(spec))
        assert "Cities attached" in msg
        assert (await history.last()).map_spec == spec

    async def test_geojson_map_attaches(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [json.dumps({"type": "Point", "coordinates": [-122.4, 37.7]})],
                "name": ["SF"],
            }
        )
        history = await _history_with(df)
        spec = {"layers": [{"type": "geojson", "geojson": "geom", "label": "name"}]}
        msg = await RenderMapTool(history=history)(record_id="Q1", map_spec=json.dumps(spec))
        assert "GeoJSON map attached" in msg
        assert (await history.last()).map_spec == spec

    async def test_unknown_column_errors_without_attaching(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "missing"}]}
        msg = await RenderMapTool(history=history)(record_id="Q1", map_spec=json.dumps(spec))
        assert "field not found" in msg and "missing" in msg
        assert (await history.last()).map_spec is None

    async def test_invalid_coordinates_error_without_attaching(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [4_547_675], "lng": [-13_627_665]}))
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(history=history)(record_id="Q1", map_spec=json.dumps(spec))
        assert "no valid latitude/longitude" in msg
        assert (await history.last()).map_spec is None

    async def test_too_many_rows_error_without_attaching(self) -> None:
        history = await _history_with(
            pd.DataFrame(
                {
                    "lat": [37.7] * (MAP_RENDER_MAX_ROWS + 1),
                    "lng": [-122.4] * (MAP_RENDER_MAX_ROWS + 1),
                }
            )
        )
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(history=history)(record_id="Q1", map_spec=json.dumps(spec))
        assert "too large to map directly" in msg
        assert f"max {MAP_RENDER_MAX_ROWS:,} rows" in msg
        assert (await history.last()).map_spec is None
