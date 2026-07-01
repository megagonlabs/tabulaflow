"""Tool that attaches a declarative map spec to a query result."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar

import pandas as pd
from pydantic_ai import Tool

from tabulaflow.toolhub.query_history import QueryHistory

MAP_RENDER_MAX_ROWS = 50_000
_GEOJSON_TYPES = {
    "Feature",
    "FeatureCollection",
    "GeometryCollection",
    "LineString",
    "MultiLineString",
    "MultiPoint",
    "MultiPolygon",
    "Point",
    "Polygon",
}


class MapSpecError(ValueError):
    """Raised when a map spec cannot be applied to a result."""


def resolve_column(df: pd.DataFrame, name: str) -> str | None:
    """Case-insensitive column name resolution."""
    for col in df.columns:
        if str(col).lower() == name.lower():
            return str(col)
    return None


def _field(df: pd.DataFrame, value: object, *, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise MapSpecError(f"{path} must be a column name")
    resolved = resolve_column(df, value)
    if resolved is None:
        raise MapSpecError(f"field not found: {value!r}. Available columns: {list(df.columns)}")
    return resolved


def _optional_field(df: pd.DataFrame, value: object, *, path: str) -> str | None:
    if value is None:
        return None
    return _field(df, value, path=path)


def _tooltip(df: pd.DataFrame, value: object, *, path: str) -> str | list[str] | bool | None:
    if value is None:
        return None
    if value is True:
        return True
    if isinstance(value, str):
        return _field(df, value, path=path)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_field(df, item, path=f"{path}[]") for item in value]
    raise MapSpecError(f"{path} must be a column name, list of column names, or true")


def _color_encoding(df: pd.DataFrame, value: object, *, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MapSpecError(f"{path} must be an object with 'field' and optional 'domain'")
    allowed = {"field", "domain"}
    unsupported = sorted(set(value) - allowed)
    if unsupported:
        raise MapSpecError(f"unsupported {path} field(s): {unsupported}")
    out = dict(value)
    out["field"] = _field(df, out.get("field"), path=f"{path}.field")
    domain = out.get("domain")
    if domain is not None and (not isinstance(domain, Sequence) or isinstance(domain, (str, bytes, bytearray))):
        raise MapSpecError(f"{path}.domain must be a list")
    return out


def _size_encoding(df: pd.DataFrame, value: object, *, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MapSpecError(f"{path} must be an object with 'field'")
    allowed = {"field"}
    unsupported = sorted(set(value) - allowed)
    if unsupported:
        raise MapSpecError(f"unsupported {path} field(s): {unsupported}")
    out = dict(value)
    out["field"] = _field(df, out.get("field"), path=f"{path}.field")
    return out


def _safe_inline_value(value: object) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _inline_field(points: Sequence[Mapping[str, object]], value: object, *, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise MapSpecError(f"{path} must be an inline point property name")
    if not any(value in point for point in points):
        raise MapSpecError(f"inline point property not found: {value!r}")
    return value


def _inline_optional_field(points: Sequence[Mapping[str, object]], value: object, *, path: str) -> str | None:
    if value is None:
        return None
    return _inline_field(points, value, path=path)


def _inline_tooltip(
    points: Sequence[Mapping[str, object]], value: object, *, path: str
) -> str | list[str] | bool | None:
    if value is None:
        return None
    if value is True:
        return True
    if isinstance(value, str):
        return _inline_field(points, value, path=path)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_inline_field(points, item, path=f"{path}[]") for item in value]
    raise MapSpecError(f"{path} must be an inline point property name, list of property names, or true")


def _inline_color_encoding(points: Sequence[Mapping[str, object]], value: object, *, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MapSpecError(f"{path} must be an object with 'field' and optional 'domain'")
    allowed = {"field", "domain"}
    unsupported = sorted(set(value) - allowed)
    if unsupported:
        raise MapSpecError(f"unsupported {path} field(s): {unsupported}")
    out = dict(value)
    out["field"] = _inline_field(points, out.get("field"), path=f"{path}.field")
    domain = out.get("domain")
    if domain is not None and (not isinstance(domain, Sequence) or isinstance(domain, (str, bytes, bytearray))):
        raise MapSpecError(f"{path}.domain must be a list")
    return out


def _inline_size_encoding(points: Sequence[Mapping[str, object]], value: object, *, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MapSpecError(f"{path} must be an object with 'field'")
    allowed = {"field"}
    unsupported = sorted(set(value) - allowed)
    if unsupported:
        raise MapSpecError(f"unsupported {path} field(s): {unsupported}")
    out = dict(value)
    out["field"] = _inline_field(points, out.get("field"), path=f"{path}.field")
    return out


def _has_valid_point(df: pd.DataFrame, lat_col: str, lng_col: str) -> bool:
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    lng = pd.to_numeric(df[lng_col], errors="coerce")
    valid = lat.between(-90, 90) & lng.between(-180, 180)
    return bool(valid.any())


def _normalize_inline_points(value: object, *, path: str) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        raise MapSpecError(f"{path} must be a non-empty list of point objects")
    points: list[dict[str, object]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise MapSpecError(f"{path}[{index}] must be an object")
        lat = raw.get("lat")
        lng = raw.get("lng")
        if isinstance(lat, bool) or isinstance(lng, bool):
            raise MapSpecError(f"{path}[{index}].lat/lng must be numbers")
        try:
            lat_num = float(lat)
            lng_num = float(lng)
        except (TypeError, ValueError):
            raise MapSpecError(f"{path}[{index}].lat/lng must be numbers") from None
        if not (-90 <= lat_num <= 90 and -180 <= lng_num <= 180):
            raise MapSpecError(f"{path}[{index}] has invalid latitude/longitude")
        point: dict[str, object] = {}
        for key, item in raw.items():
            if not isinstance(key, str) or not key:
                raise MapSpecError(f"{path}[{index}] property names must be non-empty strings")
            if not _safe_inline_value(item):
                raise MapSpecError(f"{path}[{index}].{key} must be a string, number, boolean, or null")
            point[key] = copy.deepcopy(item)
        point["lat"] = lat_num
        point["lng"] = lng_num
        points.append(point)
    return points


def _normalize_points_layer(df: pd.DataFrame, layer: Mapping[str, object], index: int) -> dict[str, Any]:
    allowed = {
        "type",
        "points",
        "lat",
        "latitude",
        "lng",
        "lon",
        "longitude",
        "label",
        "tooltip",
        "marker",
        "color",
        "size",
    }
    unsupported = sorted(set(layer) - allowed)
    if unsupported:
        raise MapSpecError(f"unsupported layers[{index}] field(s): {unsupported}")

    has_inline_points = "points" in layer
    has_column_points = any(key in layer for key in ("lat", "latitude", "lng", "lon", "longitude"))
    if has_inline_points and has_column_points:
        raise MapSpecError(f"layers[{index}] must use either points or lat/lng columns, not both")
    if not has_inline_points and not has_column_points:
        raise MapSpecError(f"layers[{index}] must define points or lat/lng columns")

    inline_points: list[dict[str, object]] | None = None
    if has_inline_points:
        inline_points = _normalize_inline_points(layer.get("points"), path=f"layers[{index}].points")
        out: dict[str, Any] = {"type": "points", "points": inline_points}
        label = _inline_optional_field(inline_points, layer.get("label"), path=f"layers[{index}].label")
        tooltip = _inline_tooltip(inline_points, layer.get("tooltip"), path=f"layers[{index}].tooltip")
    else:
        lat = _field(df, layer.get("lat") or layer.get("latitude"), path=f"layers[{index}].lat")
        lng = _field(df, layer.get("lng") or layer.get("lon") or layer.get("longitude"), path=f"layers[{index}].lng")
        if not _has_valid_point(df, lat, lng):
            raise MapSpecError(f"layers[{index}] has no valid latitude/longitude rows")
        out = {"type": "points", "lat": lat, "lng": lng}
        label = _optional_field(df, layer.get("label"), path=f"layers[{index}].label")
        tooltip = _tooltip(df, layer.get("tooltip"), path=f"layers[{index}].tooltip")
    if label is not None:
        out["label"] = label
    if tooltip is not None:
        out["tooltip"] = tooltip
    marker = layer.get("marker")
    if marker is not None:
        if not isinstance(marker, Mapping):
            raise MapSpecError(f"layers[{index}].marker must be an object")
        unsupported_marker = sorted(set(marker) - {"type"})
        if unsupported_marker:
            raise MapSpecError(f"unsupported layers[{index}].marker field(s): {unsupported_marker}")
        marker_type = marker.get("type", "pin")
        if marker_type not in {"pin", "circle"}:
            raise MapSpecError(f"layers[{index}].marker.type must be 'pin' or 'circle'")
        out["marker"] = dict(marker)
    if "color" in layer:
        out["color"] = (
            _inline_color_encoding(inline_points, layer["color"], path=f"layers[{index}].color")
            if inline_points is not None
            else _color_encoding(df, layer["color"], path=f"layers[{index}].color")
        )
    if "size" in layer:
        out["size"] = (
            _inline_size_encoding(inline_points, layer["size"], path=f"layers[{index}].size")
            if inline_points is not None
            else _size_encoding(df, layer["size"], path=f"layers[{index}].size")
        )
    return out


def _is_geojson_object(value: object) -> bool:
    return isinstance(value, Mapping) and value.get("type") in _GEOJSON_TYPES


def _looks_like_geojson_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text.startswith("{"):
        return False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False
    return _is_geojson_object(parsed)


def _has_geojson_value(df: pd.DataFrame, column: str) -> bool:
    for value in df[column].dropna().head(25):
        if _is_geojson_object(value) or _looks_like_geojson_text(value):
            return True
    return False


def _normalize_geojson_layer(df: pd.DataFrame, layer: Mapping[str, object], index: int) -> dict[str, Any]:
    allowed = {"type", "geojson", "label", "tooltip", "color"}
    unsupported = sorted(set(layer) - allowed)
    if unsupported:
        raise MapSpecError(f"unsupported layers[{index}] field(s): {unsupported}")

    geojson = layer.get("geojson")
    if isinstance(geojson, str):
        geojson_value: object = _field(df, geojson, path=f"layers[{index}].geojson")
        if not _has_geojson_value(df, str(geojson_value)):
            raise MapSpecError(f"layers[{index}].geojson has no valid GeoJSON sample values")
    elif _is_geojson_object(geojson):
        geojson_value = copy.deepcopy(geojson)
    else:
        raise MapSpecError(f"layers[{index}].geojson must be a GeoJSON column or object")

    out: dict[str, Any] = {"type": "geojson", "geojson": geojson_value}
    label = _optional_field(df, layer.get("label"), path=f"layers[{index}].label")
    if label is not None:
        out["label"] = label
    tooltip = _tooltip(df, layer.get("tooltip"), path=f"layers[{index}].tooltip")
    if tooltip is not None:
        out["tooltip"] = tooltip
    if "color" in layer:
        out["color"] = _color_encoding(df, layer["color"], path=f"layers[{index}].color")
    return out


def _normalize_view(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MapSpecError("view must be an object")
    allowed = {"fit", "center", "zoom", "maxZoom"}
    unsupported = sorted(set(value) - allowed)
    if unsupported:
        raise MapSpecError(f"unsupported view field(s): {unsupported}")
    return dict(value)


def normalize_map_spec(df: pd.DataFrame, spec: Mapping[str, object]) -> dict[str, Any]:
    """Validate and normalize a map spec against a result DataFrame."""
    allowed_top_level = {"title", "view", "layers"}
    unsupported_top_level = sorted(set(spec) - allowed_top_level)
    if unsupported_top_level:
        raise MapSpecError(f"unsupported map_spec field(s): {unsupported_top_level}")

    raw_layers = spec.get("layers")
    if not isinstance(raw_layers, Sequence) or isinstance(raw_layers, (str, bytes, bytearray)) or not raw_layers:
        raise MapSpecError("map_spec.layers must be a non-empty list")

    out: dict[str, Any] = {}
    if "title" in spec:
        out["title"] = copy.deepcopy(spec["title"])
    if "view" in spec:
        out["view"] = _normalize_view(spec["view"])

    layers: list[dict[str, Any]] = []
    for index, raw_layer in enumerate(raw_layers):
        if not isinstance(raw_layer, Mapping):
            raise MapSpecError(f"layers[{index}] must be an object")
        layer_type = raw_layer.get("type")
        if layer_type == "points":
            layers.append(_normalize_points_layer(df, raw_layer, index))
        elif layer_type == "geojson":
            layers.append(_normalize_geojson_layer(df, raw_layer, index))
        else:
            raise MapSpecError(f"layers[{index}].type must be 'points' or 'geojson'")
    out["layers"] = layers
    return out


def map_type_label(spec: Mapping[str, object]) -> str:
    """Human-readable map label for UI cards and tool messages."""
    title = spec.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    layers = spec.get("layers")
    if isinstance(layers, Sequence) and not isinstance(layers, (str, bytes, bytearray)):
        types = [layer.get("type") for layer in layers if isinstance(layer, Mapping)]
        if types == ["points"]:
            return "Point map"
        if types == ["geojson"]:
            return "GeoJSON map"
        if types:
            return "Layered map"
    return "Map"


class RenderMapTool:
    """Attach a declarative map spec to a stored query result."""

    name: ClassVar = "render_map"

    def __init__(self, history: QueryHistory | None = None) -> None:
        self._history = history or QueryHistory()

    async def __call__(self, record_id: str | None = None, *, map_spec: dict[str, Any] | str) -> str:
        """Attach a map view to a query result.

        Use for spatial results. The spec is a JSON object with a non-empty
        ``layers`` list.

        Full public V1 grammar:
        - Top level:
          ``title``: optional string.
          ``view``: optional object with ``fit`` bool, ``center`` as
          ``[lat, lng]``, ``zoom`` number, and ``maxZoom`` number.
          ``layers``: required non-empty list.
        - Common layer fields:
          ``label``: optional field name for the short feature identity.
          ``tooltip``: optional field name, list of field names, or ``true``;
          shown on hover and click.
          ``color``: optional ``{"field":"status"}`` or
          ``{"field":"status","domain":[...]}``; the output pane chooses the
          palette.
        - ``points`` layer:
          Column mode: ``{"type":"points","lat":"lat","lng":"lng"}``.
          Inline mode:
          ``{"type":"points","points":[{"lat":37.7,"lng":-122.4,"label":"Destination"}]}``.
          Add optional ``label``, ``tooltip``, ``color``, ``marker``, and
          ``size``. Inline ``label``, ``tooltip``, ``color``, and ``size``
          reference inline point property names.
          ``marker`` is ``{"type":"pin"}`` or ``{"type":"circle"}``.
          ``size`` is ``{"field":"value"}``; the output pane chooses the
          radius range.
        - ``geojson`` layer:
          ``{"type":"geojson","geojson":"geom_geojson"}`` plus optional
          ``label``, ``tooltip``, and ``color``. ``geojson`` is a column name
          or inline WGS84 GeoJSON object.

        Minimal examples:
        ``{"layers":[{"type":"points","lat":"lat","lng":"lng","label":"name","tooltip":["name","status"]}]}``
        ``{"layers":[{"type":"points","points":[{"lat":37.7,"lng":-122.4,"label":"Destination"}],"label":"label"}]}``
        ``{"layers":[{"type":"geojson","geojson":"geom_geojson","label":"name","tooltip":["name"]}]}``

        Prefer defaults unless the user asks for styling or a fixed viewport.

        If the database has native geometry, convert it to WGS84 GeoJSON in SQL
        before calling this tool, using the database's spatial functions. For
        example, PostGIS:
        ``ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom_geojson``; DuckDB
        spatial: ``ST_AsGeoJSON(ST_Transform(geom, 'EPSG:4326')) AS geom_geojson``.
        When ``record_id`` is omitted, the most recent query result is used.

        Args:
            record_id: Optional query-history record ID (e.g. ``"Q3"``).
                If omitted, use the most recent query result.
            map_spec: Declarative map specification as a JSON object or JSON
                string. GeoJSON coordinates must be WGS84 longitude/latitude.
        """
        if isinstance(map_spec, str):
            try:
                spec = json.loads(map_spec)
            except json.JSONDecodeError as e:
                return f"(error: invalid JSON — {e})"
        else:
            spec = map_spec

        if not isinstance(spec, dict):
            return "(error: map_spec must be a JSON object)"

        try:
            record = await self._history.get(record_id) if record_id else await self._history.last()
        except KeyError:
            return f"(error: unknown record_id {record_id!r})"
        except ValueError:
            return "(error: no query has been executed yet — run a query first)"

        pred = record.pred_query
        if pred.exec_result is None or pred.exec_result.df is None:
            return f"(error: query {record.record_id} returned no data)"
        df = pred.exec_result.df
        if df.empty:
            return f"(error: query {record.record_id} result is empty)"
        if len(df) > MAP_RENDER_MAX_ROWS:
            return (
                f"(error: {len(df):,} rows is too large to map directly — filter or aggregate the result first; "
                f"max {MAP_RENDER_MAX_ROWS:,} rows)"
            )

        try:
            normalized = normalize_map_spec(df, spec)
        except MapSpecError as e:
            return f"(error: {e})"

        label = map_type_label(normalized)
        self._history.attach_map(record.record_id, normalized)
        return f"{label} attached to {record.record_id} — {len(df):,} rows"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
