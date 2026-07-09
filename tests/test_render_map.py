"""Tests for the declarative map tool."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub.query_history import QueryHistory
from tabulaflow.toolhub.render_map import MAP_RENDER_MAX_ROWS, RenderMapTool, normalize_map_spec


async def _history_with(*dfs: pd.DataFrame) -> QueryHistory:
    history = QueryHistory()
    for df in dfs:
        await history.add("db", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=df)))
    return history


def _norm(spec: dict[str, Any], **sources: pd.DataFrame) -> dict[str, Any]:
    return normalize_map_spec(spec, sources)


class TestNormalizeMapSpec:
    def test_points_layer_resolves_fields_case_insensitively(self) -> None:
        df = pd.DataFrame({"Lat": [37.7], "Lng": [-122.4], "Name": ["SF"]})
        spec = {"layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "lng", "label": "name"}]}
        assert _norm(spec, Q1=df) == {
            "layers": [{"type": "points", "source": "Q1", "lat": "Lat", "lng": "Lng", "label": "Name"}]
        }

    def test_points_layer_allows_mixed_missing_coordinates(self) -> None:
        df = pd.DataFrame(
            {
                "lat": [None, 37.7, 999],
                "lng": [-122.4, -122.4, -122.4],
                "name": ["missing", "valid", "invalid"],
            }
        )
        spec = {"layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "lng", "label": "name"}]}
        assert _norm(spec, Q1=df) == {
            "layers": [{"type": "points", "source": "Q1", "lat": "lat", "lng": "lng", "label": "name"}]
        }

    def test_points_layer_accepts_inline_points(self) -> None:
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
        # Inline layers carry their own data and need no source record.
        assert _norm(spec) == spec

    def test_inline_points_reject_record_id(self) -> None:
        spec = {"layers": [{"type": "points", "record_id": "Q1", "points": [{"lat": 37.7, "lng": -122.4}]}]}
        with pytest.raises(ValueError, match="inline points layers must not set record_id"):
            _norm(spec, Q1=pd.DataFrame({"x": [1]}))

    def test_column_points_require_record_id(self) -> None:
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        with pytest.raises(ValueError, match="points layers must set record_id"):
            _norm(spec, Q1=pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))

    def test_inline_points_are_mutually_exclusive_with_column_points(self) -> None:
        spec = {
            "layers": [
                {
                    "type": "points",
                    "record_id": "Q1",
                    "lat": "lat",
                    "lng": "lng",
                    "points": [{"lat": 37.7, "lng": -122.4}],
                }
            ]
        }
        with pytest.raises(ValueError, match="either points or lat/lng columns"):
            _norm(spec, Q1=pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))

    def test_inline_points_validate_coordinates_and_properties(self) -> None:
        cases: list[dict[str, Any]] = [
            {"layers": [{"type": "points", "points": [{"lat": None, "lng": -122.4}]}]},
            {"layers": [{"type": "points", "points": [{"lat": 999, "lng": -122.4}]}]},
            {"layers": [{"type": "points", "points": [{"lat": 37.7, "lng": -122.4, "meta": {"x": 1}}]}]},
            {"layers": [{"type": "points", "points": [{"lat": 37.7, "lng": -122.4}], "label": "missing"}]},
        ]
        for spec in cases:
            with pytest.raises(ValueError):
                _norm(spec)

    def test_geojson_layer_accepts_column(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}],
                "name": ["SF"],
            }
        )
        spec = {"layers": [{"type": "geojson", "record_id": "Q1", "geojson": "geom", "tooltip": ["name"]}]}
        assert _norm(spec, Q1=df) == {
            "layers": [{"type": "geojson", "source": "Q1", "geojson": "geom", "tooltip": ["name"]}]
        }

    def test_geojson_column_requires_record_id(self) -> None:
        df = pd.DataFrame({"geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}]})
        spec = {"layers": [{"type": "geojson", "geojson": "geom"}]}
        with pytest.raises(ValueError, match="geojson layers must set record_id"):
            _norm(spec, Q1=df)

    def test_custom_basemap_is_rejected(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4]})
        spec = {
            "basemap": {"type": "tile", "tileUrl": "https://example.com/{z}/{x}/{y}.png"},
            "layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "lng"}],
        }
        with pytest.raises(ValueError, match="unsupported map_spec field"):
            _norm(spec, Q1=df)

    def test_raw_styling_fields_are_rejected(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}],
                "status": ["open"],
                "value": [10],
            }
        )
        cases: list[dict[str, Any]] = [
            {"layers": [{"type": "geojson", "record_id": "Q1", "geojson": "geom", "style": {"weight": 1}}]},
            {"layers": [{"type": "geojson", "record_id": "Q1", "geojson": "geom", "color": "#3eb489"}]},
            {
                "layers": [
                    {
                        "type": "geojson",
                        "record_id": "Q1",
                        "geojson": "geom",
                        "color": {"field": "status", "range": ["#3eb489"]},
                    }
                ]
            },
            {"layers": [{"type": "points", "record_id": "Q1", "lat": "value", "lng": "value", "size": 12}]},
            {
                "layers": [
                    {
                        "type": "points",
                        "record_id": "Q1",
                        "lat": "value",
                        "lng": "value",
                        "size": {"field": "value", "range": [5, 18]},
                    }
                ]
            },
        ]
        for spec in cases:
            with pytest.raises(ValueError):
                _norm(spec, Q1=df)

    def test_semantic_color_and_size_encodings_are_kept(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "status": ["open"], "value": [10]})
        spec = {
            "layers": [
                {
                    "type": "points",
                    "record_id": "Q1",
                    "lat": "lat",
                    "lng": "lng",
                    "color": {"field": "status", "domain": ["open", "closed"]},
                    "size": {"field": "value"},
                }
            ]
        }
        assert _norm(spec, Q1=df) == {
            "layers": [
                {
                    "type": "points",
                    "source": "Q1",
                    "lat": "lat",
                    "lng": "lng",
                    "color": {"field": "status", "domain": ["open", "closed"]},
                    "size": {"field": "value"},
                }
            ]
        }

    def test_legend_is_not_agent_facing_map_spec(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "status": ["open"]})
        spec = {
            "legend": True,
            "layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "lng", "color": {"field": "status"}}],
        }
        with pytest.raises(ValueError, match="unsupported map_spec field"):
            _norm(spec, Q1=df)

    def test_multi_record_overlay_tags_each_layer_with_its_source(self) -> None:
        boundaries = pd.DataFrame({"geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}], "area": ["A"]})
        points = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "name": ["SF"]})
        spec = {
            "layers": [
                {"type": "geojson", "record_id": "Q1", "geojson": "geom", "label": "area"},
                {"type": "points", "record_id": "Q2", "lat": "lat", "lng": "lng", "label": "name"},
            ]
        }
        assert _norm(spec, Q1=boundaries, Q2=points) == {
            "layers": [
                {"type": "geojson", "source": "Q1", "geojson": "geom", "label": "area"},
                {"type": "points", "source": "Q2", "lat": "lat", "lng": "lng", "label": "name"},
            ]
        }


class TestRenderMapTool:
    def test_tool_description_mentions_url_tooltip_links(self) -> None:
        doc = RenderMapTool.__call__.__doc__
        assert doc is not None
        assert "URLs render as links" in doc

    async def test_column_layer_missing_record_id_errors(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "record_id" in msg
        assert history._maps == {}

    async def test_points_map_created(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4], "name": ["SF"]}))
        spec = {
            "title": "Cities",
            "layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "lng", "label": "name"}],
        }
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "Map MAP1 created from Q1" in msg
        assert history.get_map("MAP1").map_spec == {
            "title": "Cities",
            "layers": [{"type": "points", "source": "Q1", "lat": "lat", "lng": "lng", "label": "name"}],
        }

    async def test_geojson_map_created(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [json.dumps({"type": "Point", "coordinates": [-122.4, 37.7]})],
                "name": ["SF"],
            }
        )
        history = await _history_with(df)
        spec = {"layers": [{"type": "geojson", "record_id": "Q1", "geojson": "geom", "label": "name"}]}
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "Map MAP1 created" in msg
        assert history.get_map("MAP1").map_spec == {
            "layers": [{"type": "geojson", "source": "Q1", "geojson": "geom", "label": "name"}]
        }

    async def test_multi_record_map_created_from_two_sources(self) -> None:
        boundaries = pd.DataFrame(
            {"geom": [json.dumps({"type": "Point", "coordinates": [-122.4, 37.7]})], "area": ["A"]}
        )
        points = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "name": ["SF"]})
        history = await _history_with(boundaries, points)
        spec = {
            "layers": [
                {"type": "geojson", "record_id": "Q1", "geojson": "geom", "label": "area"},
                {"type": "points", "record_id": "Q2", "lat": "lat", "lng": "lng", "label": "name"},
            ]
        }
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "MAP1 created from Q1, Q2" in msg
        stored = history.get_map("MAP1").map_spec
        assert [layer["source"] for layer in stored["layers"]] == ["Q1", "Q2"]

    async def test_unknown_record_id_errors_without_creating(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "record_id": "Q9", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "unknown record_id" in msg
        assert history._maps == {}

    async def test_unknown_column_errors_without_creating(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "missing"}]}
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "field not found" in msg and "missing" in msg
        assert history._maps == {}

    async def test_invalid_coordinates_error_without_creating(self) -> None:
        history = await _history_with(pd.DataFrame({"lat": [4_547_675], "lng": [-13_627_665]}))
        spec = {"layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "no valid latitude/longitude" in msg
        assert history._maps == {}

    async def test_too_many_rows_error_without_creating(self) -> None:
        history = await _history_with(
            pd.DataFrame(
                {
                    "lat": [37.7] * (MAP_RENDER_MAX_ROWS + 1),
                    "lng": [-122.4] * (MAP_RENDER_MAX_ROWS + 1),
                }
            )
        )
        spec = {"layers": [{"type": "points", "record_id": "Q1", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(history=history)(map_spec=json.dumps(spec))
        assert "too large to map directly" in msg
        assert f"max {MAP_RENDER_MAX_ROWS:,} rows" in msg
        assert history._maps == {}
