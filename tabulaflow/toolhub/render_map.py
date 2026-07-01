"""Tool that attaches a declarative map spec to a query result."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Annotated, Any, ClassVar, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
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


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _ColorEncoding(_StrictModel):
    field: str
    domain: list[Any] | None = None


class _SizeEncoding(_StrictModel):
    field: str


class _MarkerSpec(_StrictModel):
    type: Literal["pin", "circle"] = "pin"


class _MapView(_StrictModel):
    fit: Any | None = None
    center: Any | None = None
    zoom: Any | None = None
    maxZoom: Any | None = None


class _InlinePoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    lat: float
    lng: float

    @field_validator("lat", "lng", mode="before")
    @classmethod
    def _reject_bool_coordinates(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("lat/lng must be numbers")
        return value

    @model_validator(mode="after")
    def _validate_point(self) -> _InlinePoint:
        if not (-90 <= self.lat <= 90 and -180 <= self.lng <= 180):
            raise ValueError("invalid latitude/longitude")
        for key, value in (self.__pydantic_extra__ or {}).items():
            if not key:
                raise ValueError("property names must be non-empty strings")
            if value is not None and not isinstance(value, str | int | float | bool):
                raise ValueError(f"{key} must be a string, number, boolean, or null")
        return self

    def to_payload(self) -> dict[str, object]:
        """Return the inline point as the browser payload expects it."""
        point = copy.deepcopy(self.__pydantic_extra__ or {})
        point["lat"] = self.lat
        point["lng"] = self.lng
        return point


class _PointsLayer(_StrictModel):
    type: Literal["points"]
    points: list[_InlinePoint] | None = None
    lat: str | None = None
    latitude: str | None = None
    lng: str | None = None
    lon: str | None = None
    longitude: str | None = None
    label: str | None = None
    tooltip: str | list[str] | Literal[True] | None = None
    marker: _MarkerSpec | None = None
    color: _ColorEncoding | None = None
    size: _SizeEncoding | None = None

    @model_validator(mode="after")
    def _validate_point_mode(self) -> _PointsLayer:
        has_inline_points = self.points is not None
        has_column_points = any(
            value is not None for value in (self.lat, self.latitude, self.lng, self.lon, self.longitude)
        )
        if has_inline_points and has_column_points:
            raise ValueError("points layers must use either points or lat/lng columns, not both")
        if not has_inline_points and not has_column_points:
            raise ValueError("points layers must define points or lat/lng columns")
        return self


class _GeoJsonLayer(_StrictModel):
    type: Literal["geojson"]
    geojson: str | dict[str, Any]
    label: str | None = None
    tooltip: str | list[str] | Literal[True] | None = None
    color: _ColorEncoding | None = None


_Layer = Annotated[_PointsLayer | _GeoJsonLayer, Field(discriminator="type")]


class _MapSpec(_StrictModel):
    title: Any | None = None
    view: _MapView | None = None
    layers: list[_Layer]

    @field_validator("layers")
    @classmethod
    def _require_layers(cls, value: list[_Layer]) -> list[_Layer]:
        if not value:
            raise ValueError("map_spec.layers must be a non-empty list")
        return value


def resolve_column(df: pd.DataFrame, name: str) -> str | None:
    """Case-insensitive column name resolution."""
    for col in df.columns:
        if str(col).lower() == name.lower():
            return str(col)
    return None


def _validation_message(error: ValidationError) -> str:
    errors = error.errors()
    unsupported_top_level: list[str] = []
    for item in errors:
        loc = item.get("loc", ())
        if item.get("type") == "extra_forbidden" and len(loc) == 1:
            unsupported_top_level.append(str(loc[0]))
    unsupported_top_level.sort()
    if unsupported_top_level:
        return f"unsupported map_spec field(s): {unsupported_top_level}"
    if errors:
        first = errors[0]
        ctx_error = first.get("ctx", {}).get("error")
        if ctx_error is not None:
            return str(ctx_error)
        loc_text = ".".join(str(part) for part in first.get("loc", ()) if part not in {"points", "geojson"})
        msg = str(first.get("msg", "invalid map_spec"))
        return f"{loc_text}: {msg}" if loc_text else msg
    return "invalid map_spec"


def _field(df: pd.DataFrame, value: str | None, *, path: str) -> str:
    if not value:
        raise MapSpecError(f"{path} must be a column name")
    resolved = resolve_column(df, value)
    if resolved is None:
        raise MapSpecError(f"field not found: {value!r}. Available columns: {list(df.columns)}")
    return resolved


def _inline_field(points: Sequence[Mapping[str, object]], value: str | None, *, path: str) -> str:
    if not value:
        raise MapSpecError(f"{path} must be an inline point property name")
    if not any(value in point for point in points):
        raise MapSpecError(f"inline point property not found: {value!r}")
    return value


def _optional_field(resolve_field: Callable[..., str], value: str | None, *, path: str) -> str | None:
    if value is None:
        return None
    return resolve_field(value, path=path)


def _tooltip(
    resolve_field: Callable[..., str], value: str | list[str] | Literal[True] | None, *, path: str
) -> str | list[str] | bool | None:
    if value is None:
        return None
    if value is True:
        return True
    if isinstance(value, str):
        return resolve_field(value, path=path)
    return [resolve_field(item, path=f"{path}[]") for item in value]


def _color_encoding(
    resolve_field: Callable[..., str], value: _ColorEncoding | None, *, path: str
) -> dict[str, Any] | None:
    if value is None:
        return None
    out = value.model_dump(exclude_none=True)
    out["field"] = resolve_field(value.field, path=f"{path}.field")
    return out


def _size_encoding(
    resolve_field: Callable[..., str], value: _SizeEncoding | None, *, path: str
) -> dict[str, Any] | None:
    if value is None:
        return None
    out = value.model_dump()
    out["field"] = resolve_field(value.field, path=f"{path}.field")
    return out


def _has_valid_point(df: pd.DataFrame, lat_col: str, lng_col: str) -> bool:
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    lng = pd.to_numeric(df[lng_col], errors="coerce")
    valid = lat.between(-90, 90) & lng.between(-180, 180)
    return bool(valid.any())


def _normalize_points_layer(df: pd.DataFrame, layer: _PointsLayer, index: int) -> dict[str, Any]:
    if layer.points is not None:
        inline_points = [point.to_payload() for point in layer.points]

        def resolve_field(value: str | None, *, path: str) -> str:
            return _inline_field(inline_points, value, path=path)

        out: dict[str, Any] = {"type": "points", "points": inline_points}
    else:
        lat = _field(df, layer.lat or layer.latitude, path=f"layers[{index}].lat")
        lng = _field(df, layer.lng or layer.lon or layer.longitude, path=f"layers[{index}].lng")
        if not _has_valid_point(df, lat, lng):
            raise MapSpecError(f"layers[{index}] has no valid latitude/longitude rows")
        out = {"type": "points", "lat": lat, "lng": lng}

        def resolve_field(value: str | None, *, path: str) -> str:
            return _field(df, value, path=path)

    label = _optional_field(resolve_field, layer.label, path=f"layers[{index}].label")
    tooltip = _tooltip(resolve_field, layer.tooltip, path=f"layers[{index}].tooltip")
    if label is not None:
        out["label"] = label
    if tooltip is not None:
        out["tooltip"] = tooltip
    if layer.marker is not None:
        out["marker"] = layer.marker.model_dump()
    color = _color_encoding(resolve_field, layer.color, path=f"layers[{index}].color")
    if color is not None:
        out["color"] = color
    size = _size_encoding(resolve_field, layer.size, path=f"layers[{index}].size")
    if size is not None:
        out["size"] = size
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


def _normalize_geojson_layer(df: pd.DataFrame, layer: _GeoJsonLayer, index: int) -> dict[str, Any]:
    geojson = layer.geojson
    if isinstance(geojson, str):
        geojson_value: object = _field(df, geojson, path=f"layers[{index}].geojson")
        if not _has_geojson_value(df, str(geojson_value)):
            raise MapSpecError(f"layers[{index}].geojson has no valid GeoJSON sample values")
    elif _is_geojson_object(geojson):
        geojson_value = copy.deepcopy(geojson)
    else:
        raise MapSpecError(f"layers[{index}].geojson must be a GeoJSON column or object")

    out: dict[str, Any] = {"type": "geojson", "geojson": geojson_value}

    def resolve_field(value: str | None, *, path: str) -> str:
        return _field(df, value, path=path)

    label = _optional_field(resolve_field, layer.label, path=f"layers[{index}].label")
    if label is not None:
        out["label"] = label
    tooltip = _tooltip(resolve_field, layer.tooltip, path=f"layers[{index}].tooltip")
    if tooltip is not None:
        out["tooltip"] = tooltip
    color = _color_encoding(resolve_field, layer.color, path=f"layers[{index}].color")
    if color is not None:
        out["color"] = color
    return out


def normalize_map_spec(df: pd.DataFrame, spec: Mapping[str, object]) -> dict[str, Any]:
    """Validate and normalize a map spec against a result DataFrame."""
    try:
        parsed = _MapSpec.model_validate(spec)
    except ValidationError as e:
        raise MapSpecError(_validation_message(e)) from None

    out: dict[str, Any] = {}
    if "title" in spec:
        out["title"] = copy.deepcopy(parsed.title)
    if parsed.view is not None:
        out["view"] = parsed.view.model_dump(exclude_none=True)

    layers: list[dict[str, Any]] = []
    for index, layer in enumerate(parsed.layers):
        if isinstance(layer, _PointsLayer):
            layers.append(_normalize_points_layer(df, layer, index))
        elif isinstance(layer, _GeoJsonLayer):
            layers.append(_normalize_geojson_layer(df, layer, index))
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

    async def __call__(self, record_id: str, *, map_spec: str) -> str:
        """Attach a map view to a query result.

        Use for spatial results. The spec is a JSON string containing an object
        with a non-empty ``layers`` list.

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

        Args:
            record_id: Query-history record ID (e.g. ``"Q3"``).
            map_spec: Declarative map specification as a JSON string. GeoJSON
                coordinates must be WGS84 longitude/latitude.
        """
        if not isinstance(record_id, str) or not record_id.strip():
            return "(error: record_id must be a non-empty string)"

        try:
            spec = json.loads(map_spec)
        except (json.JSONDecodeError, TypeError) as e:
            return f"(error: invalid JSON — {e})"

        if not isinstance(spec, dict):
            return "(error: map_spec must be a JSON object)"

        try:
            record = await self._history.get(record_id)
        except KeyError:
            return f"(error: unknown record_id {record_id!r})"

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
