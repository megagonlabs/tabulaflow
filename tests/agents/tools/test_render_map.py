"""Tests for the declarative map tool."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

from tabulaflow.core import ExecResult
from tabulaflow.output.specs import ChoiceOption, ChoiceParameter, MapArtifactSpec
from tabulaflow.output.store import OutputStore
from tabulaflow.agents.tools.render_map import RenderMapTool
from tabulaflow.output.maps import (
    ColorEncodingSpec,
    GeoJsonLayerSpec,
    InlinePointSpec,
    MapSpec,
    MapViewSpec,
    MarkerSpec,
    PointsLayerSpec,
    SizeEncodingSpec,
    normalize_map_spec,
    parse_map_spec,
)


async def _output_store_with(*dfs: pd.DataFrame) -> OutputStore:
    output_store = OutputStore()
    for df in dfs:
        await output_store.add_fixed_result_source("db", "duckdb", "SELECT 1", ExecResult(df=df))
    return output_store


def _map_artifact(output_store: OutputStore, map_id: str) -> MapArtifactSpec:
    artifact = output_store.get_artifact(map_id)
    assert isinstance(artifact, MapArtifactSpec)
    return artifact


def _norm(spec: dict[str, Any], **sources: pd.DataFrame) -> dict[str, Any]:
    return normalize_map_spec(spec, sources)


class TestNormalizeMapSpec:
    def test_public_nested_models_construct_map_spec(self) -> None:
        spec = MapSpec(
            view=MapViewSpec(zoom=4),
            layers=[
                PointsLayerSpec(
                    type="points",
                    points=[InlinePointSpec(lat=1, lng=2)],
                    marker=MarkerSpec(type="circle"),
                    color=ColorEncodingSpec(field="lat"),
                    size=SizeEncodingSpec(field="lng"),
                ),
                GeoJsonLayerSpec(type="geojson", geojson={"type": "Point", "coordinates": [2, 1]}),
            ],
        )

        assert len(spec.layers) == 2

    def test_map_view_uses_typed_fields_and_serializes_max_zoom(self) -> None:
        spec = MapSpec(
            title="Places",
            view=MapViewSpec(fit=True, center=(37.7, -122.4), zoom=4, max_zoom=12),
            layers=[PointsLayerSpec(type="points", points=[InlinePointSpec(lat=37.7, lng=-122.4)])],
        )

        assert normalize_map_spec(spec, {})["view"] == {
            "fit": True,
            "center": (37.7, -122.4),
            "zoom": 4.0,
            "maxZoom": 12.0,
        }

    def test_map_view_rejects_invalid_center(self) -> None:
        with pytest.raises(ValueError, match="invalid map center"):
            MapViewSpec(center=(100, 0))

    def test_parse_returns_public_map_spec(self) -> None:
        parsed = parse_map_spec({"layers": [{"type": "points", "points": [{"lat": 1, "lng": 2}]}]})

        assert isinstance(parsed, MapSpec)

    def test_points_layer_resolves_fields_case_insensitively(self) -> None:
        df = pd.DataFrame({"Lat": [37.7], "Lng": [-122.4], "Name": ["SF"]})
        spec = {"layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng", "label": "name"}]}
        assert _norm(spec, S1=df) == {
            "layers": [{"type": "points", "source_id": "S1", "lat": "Lat", "lng": "Lng", "label": "Name"}]
        }

    def test_points_layer_allows_mixed_missing_coordinates(self) -> None:
        df = pd.DataFrame(
            {
                "lat": [None, 37.7, 999],
                "lng": [-122.4, -122.4, -122.4],
                "name": ["missing", "valid", "invalid"],
            }
        )
        spec = {"layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng", "label": "name"}]}
        assert _norm(spec, S1=df) == {
            "layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng", "label": "name"}]
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
        # Inline layers carry their own data and need no source.
        assert _norm(spec) == spec

    def test_inline_points_reject_source_id(self) -> None:
        spec = {"layers": [{"type": "points", "source_id": "S1", "points": [{"lat": 37.7, "lng": -122.4}]}]}
        with pytest.raises(ValueError, match="inline points layers must not set source_id"):
            _norm(spec, S1=pd.DataFrame({"x": [1]}))

    def test_column_points_require_source_id(self) -> None:
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        with pytest.raises(ValueError, match="points layers must set source_id"):
            _norm(spec, S1=pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))

    def test_inline_points_are_mutually_exclusive_with_column_points(self) -> None:
        spec = {
            "layers": [
                {
                    "type": "points",
                    "source_id": "S1",
                    "lat": "lat",
                    "lng": "lng",
                    "points": [{"lat": 37.7, "lng": -122.4}],
                }
            ]
        }
        with pytest.raises(ValueError, match="either points or lat/lng columns"):
            _norm(spec, S1=pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))

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
        spec = {"layers": [{"type": "geojson", "source_id": "S1", "geojson": "geom", "tooltip": ["name"]}]}
        assert _norm(spec, S1=df) == {
            "layers": [{"type": "geojson", "source_id": "S1", "geojson": "geom", "tooltip": ["name"]}]
        }

    def test_geojson_column_requires_source_id(self) -> None:
        df = pd.DataFrame({"geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}]})
        spec = {"layers": [{"type": "geojson", "geojson": "geom"}]}
        with pytest.raises(ValueError, match="geojson layers must set source_id"):
            _norm(spec, S1=df)

    def test_custom_basemap_is_rejected(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4]})
        spec = {
            "basemap": {"type": "tile", "tileUrl": "https://example.com/{z}/{x}/{y}.png"},
            "layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng"}],
        }
        with pytest.raises(ValueError, match="unsupported map_spec field"):
            _norm(spec, S1=df)

    def test_raw_styling_fields_are_rejected(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}],
                "status": ["open"],
                "value": [10],
            }
        )
        cases: list[dict[str, Any]] = [
            {"layers": [{"type": "geojson", "source_id": "S1", "geojson": "geom", "style": {"weight": 1}}]},
            {"layers": [{"type": "geojson", "source_id": "S1", "geojson": "geom", "color": "#3eb489"}]},
            {
                "layers": [
                    {
                        "type": "geojson",
                        "source_id": "S1",
                        "geojson": "geom",
                        "color": {"field": "status", "range": ["#3eb489"]},
                    }
                ]
            },
            {
                "layers": [
                    {
                        "type": "points",
                        "source_id": "S1",
                        "lat": "value",
                        "lng": "value",
                        "size": {"field": "value", "domain": [10, 5]},
                    }
                ]
            },
            {"layers": [{"type": "points", "source_id": "S1", "lat": "value", "lng": "value", "size": 12}]},
            {
                "layers": [
                    {
                        "type": "points",
                        "source_id": "S1",
                        "lat": "value",
                        "lng": "value",
                        "size": {"field": "value", "range": [5, 18]},
                    }
                ]
            },
        ]
        for spec in cases:
            with pytest.raises(ValueError):
                _norm(spec, S1=df)

    def test_semantic_color_and_size_encodings_are_kept(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "status": ["open"], "value": [10]})
        spec = {
            "layers": [
                {
                    "type": "points",
                    "source_id": "S1",
                    "lat": "lat",
                    "lng": "lng",
                    "color": {"field": "status", "domain": ["open", "closed"]},
                    "size": {"field": "value", "domain": [0, 100]},
                }
            ]
        }
        assert _norm(spec, S1=df) == {
            "layers": [
                {
                    "type": "points",
                    "source_id": "S1",
                    "lat": "lat",
                    "lng": "lng",
                    "color": {"field": "status", "domain": ["open", "closed"]},
                    "size": {"field": "value", "domain": [0.0, 100.0]},
                }
            ]
        }

    def test_legend_is_not_agent_facing_map_spec(self) -> None:
        df = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "status": ["open"]})
        spec = {
            "legend": True,
            "layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng", "color": {"field": "status"}}],
        }
        with pytest.raises(ValueError, match="unsupported map_spec field"):
            _norm(spec, S1=df)

    def test_multi_source_overlay_tags_each_layer_with_its_source(self) -> None:
        boundaries = pd.DataFrame({"geom": [{"type": "Point", "coordinates": [-122.4, 37.7]}], "area": ["A"]})
        points = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "name": ["SF"]})
        spec = {
            "layers": [
                {"type": "geojson", "source_id": "S1", "geojson": "geom", "label": "area"},
                {"type": "points", "source_id": "S2", "lat": "lat", "lng": "lng", "label": "name"},
            ]
        }
        assert _norm(spec, S1=boundaries, S2=points) == {
            "layers": [
                {"type": "geojson", "source_id": "S1", "geojson": "geom", "label": "area"},
                {"type": "points", "source_id": "S2", "lat": "lat", "lng": "lng", "label": "name"},
            ]
        }


class TestRenderMapTool:
    async def test_parameterized_source_uses_default_selection(self) -> None:
        output_store = OutputStore()
        source = output_store.add_parameterized_source(
            "db",
            [
                ChoiceParameter(
                    id="period",
                    label="Period",
                    choices=[ChoiceOption(id="q1", label="Q1"), ChoiceOption(id="q2", label="Q2")],
                )
            ],
            "SELECT 1",
        )
        await output_store.cache_parameterized_result(
            source.id,
            "duckdb",
            {"period": "q1"},
            "SELECT 1",
            ExecResult(df=pd.DataFrame({"lat": [37.7], "lng": [-122.4]})),
        )
        spec = {"layers": [{"type": "points", "source_id": source.id, "lat": "lat", "lng": "lng"}]}

        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))

        assert "Map MAP1 created from S1" in msg

    def test_tool_description_mentions_url_tooltip_links(self) -> None:
        doc = RenderMapTool.__call__.__doc__
        assert doc is not None
        # Whitespace-normalized: the phrase may wrap across docstring lines.
        assert "URLs render as links" in " ".join(doc.split())

    async def test_column_layer_missing_source_id_errors(self) -> None:
        output_store = await _output_store_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "source_id" in msg
        assert output_store._artifacts == {}

    async def test_points_map_created(self) -> None:
        output_store = await _output_store_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4], "name": ["SF"]}))
        spec = {
            "title": "Cities",
            "layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng", "label": "name"}],
        }
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "Map MAP1 created from S1" in msg
        assert _map_artifact(output_store, "MAP1").spec == {
            "title": "Cities",
            "layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng", "label": "name"}],
        }

    async def test_geojson_map_created(self) -> None:
        df = pd.DataFrame(
            {
                "geom": [json.dumps({"type": "Point", "coordinates": [-122.4, 37.7]})],
                "name": ["SF"],
            }
        )
        output_store = await _output_store_with(df)
        spec = {"layers": [{"type": "geojson", "source_id": "S1", "geojson": "geom", "label": "name"}]}
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "Map MAP1 created" in msg
        assert _map_artifact(output_store, "MAP1").spec == {
            "layers": [{"type": "geojson", "source_id": "S1", "geojson": "geom", "label": "name"}]
        }

    async def test_multi_source_map_created_from_two_sources(self) -> None:
        boundaries = pd.DataFrame(
            {"geom": [json.dumps({"type": "Point", "coordinates": [-122.4, 37.7]})], "area": ["A"]}
        )
        points = pd.DataFrame({"lat": [37.7], "lng": [-122.4], "name": ["SF"]})
        output_store = await _output_store_with(boundaries, points)
        spec = {
            "layers": [
                {"type": "geojson", "source_id": "S1", "geojson": "geom", "label": "area"},
                {"type": "points", "source_id": "S2", "lat": "lat", "lng": "lng", "label": "name"},
            ]
        }
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "MAP1 created from S1, S2" in msg
        stored = _map_artifact(output_store, "MAP1").spec
        assert [layer["source_id"] for layer in stored["layers"]] == ["S1", "S2"]

    async def test_unknown_source_id_errors_without_creating(self) -> None:
        output_store = await _output_store_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "source_id": "S9", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "unknown source_id" in msg
        assert output_store._artifacts == {}

    async def test_unknown_column_errors_without_creating(self) -> None:
        output_store = await _output_store_with(pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))
        spec = {"layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "missing"}]}
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "field not found" in msg and "missing" in msg
        assert output_store._artifacts == {}

    async def test_invalid_coordinates_error_without_creating(self) -> None:
        output_store = await _output_store_with(pd.DataFrame({"lat": [4_547_675], "lng": [-13_627_665]}))
        spec = {"layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "no valid latitude/longitude" in msg
        assert output_store._artifacts == {}

    async def test_too_many_rows_error_without_creating(self) -> None:
        output_store = await _output_store_with(
            pd.DataFrame(
                {
                    "lat": [37.7] * 50_001,
                    "lng": [-122.4] * 50_001,
                }
            )
        )
        spec = {"layers": [{"type": "points", "source_id": "S1", "lat": "lat", "lng": "lng"}]}
        msg = await RenderMapTool(output_store=output_store)(map_spec=json.dumps(spec))
        assert "too large to map directly" in msg
        assert "max 50,000 rows" in msg
        assert output_store._artifacts == {}
