"""Map specification parsing and normalization."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Annotated, Any, Literal, TypeAlias

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


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

__all__ = [
    "ColorEncodingSpec",
    "GeoJsonLayerSpec",
    "InlinePointSpec",
    "MAP_RENDER_MAX_ROWS",
    "MapLayerSpec",
    "MapSpec",
    "MapSpecError",
    "MapViewSpec",
    "MarkerSpec",
    "PointsLayerSpec",
    "SizeEncodingSpec",
    "normalize_map_spec",
    "parse_map_spec",
    "referenced_source_ids",
]


class MapSpecError(ValueError):
    """Raised when a map spec cannot be applied to a result."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ColorEncodingSpec(_StrictModel):
    """Color encoding driven by a source field."""

    field: str
    domain: list[Any] | None = None


class SizeEncodingSpec(_StrictModel):
    """Marker-size encoding driven by a source field."""

    field: str


class MarkerSpec(_StrictModel):
    """Point marker style."""

    type: Literal["pin", "circle"] = "pin"


class MapViewSpec(_StrictModel):
    """Initial map viewport configuration."""

    fit: Any | None = None
    center: Any | None = None
    zoom: Any | None = None
    maxZoom: Any | None = None


class InlinePointSpec(BaseModel):
    """One inline geographic point and its scalar properties."""

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
    def _validate_point(self) -> InlinePointSpec:
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


class PointsLayerSpec(_StrictModel):
    """Point layer backed by columns or inline points."""

    type: Literal["points"]
    source_id: str | None = None
    points: list[InlinePointSpec] | None = None
    lat: str | None = None
    latitude: str | None = None
    lng: str | None = None
    lon: str | None = None
    longitude: str | None = None
    label: str | None = None
    tooltip: str | list[str] | Literal[True] | None = None
    marker: MarkerSpec | None = None
    color: ColorEncodingSpec | None = None
    size: SizeEncodingSpec | None = None

    @model_validator(mode="after")
    def _validate_point_mode(self) -> PointsLayerSpec:
        has_inline_points = self.points is not None
        has_column_points = any(
            value is not None for value in (self.lat, self.latitude, self.lng, self.lon, self.longitude)
        )
        if has_inline_points and has_column_points:
            raise ValueError("points layers must use either points or lat/lng columns, not both")
        if not has_inline_points and not has_column_points:
            raise ValueError("points layers must define points or lat/lng columns")
        if has_inline_points and self.source_id is not None:
            raise ValueError("inline points layers must not set source_id")
        if has_column_points and self.source_id is None:
            raise ValueError("points layers must set source_id")
        return self


class GeoJsonLayerSpec(_StrictModel):
    """GeoJSON layer backed by a column or inline GeoJSON."""

    type: Literal["geojson"]
    source_id: str | None = None
    geojson: str | dict[str, Any]
    label: str | None = None
    tooltip: str | list[str] | Literal[True] | None = None
    color: ColorEncodingSpec | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> GeoJsonLayerSpec:
        is_column = isinstance(self.geojson, str)
        if is_column and self.source_id is None:
            raise ValueError("geojson layers must set source_id")
        if not is_column and self.source_id is None and (self.label or self.tooltip or self.color):
            raise ValueError("inline geojson with label/tooltip/color must set source_id")
        return self


MapLayerSpec: TypeAlias = Annotated[PointsLayerSpec | GeoJsonLayerSpec, Field(discriminator="type")]


class MapSpec(_StrictModel):
    """Declarative map specification."""

    title: Any | None = None
    view: MapViewSpec | None = None
    layers: list[MapLayerSpec]

    @field_validator("layers")
    @classmethod
    def _require_layers(cls, value: list[MapLayerSpec]) -> list[MapLayerSpec]:
        if not value:
            raise ValueError("map_spec.layers must be a non-empty list")
        return value


def _resolve_column(df: pd.DataFrame, name: str) -> str | None:
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
    resolved = _resolve_column(df, value)
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
    resolve_field: Callable[..., str], value: ColorEncodingSpec | None, *, path: str
) -> dict[str, Any] | None:
    if value is None:
        return None
    out = value.model_dump(exclude_none=True)
    out["field"] = resolve_field(value.field, path=f"{path}.field")
    return out


def _size_encoding(
    resolve_field: Callable[..., str], value: SizeEncodingSpec | None, *, path: str
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


def _normalize_points_layer(df: pd.DataFrame | None, layer: PointsLayerSpec, index: int) -> dict[str, Any]:
    if layer.points is not None:
        inline_points = [point.to_payload() for point in layer.points]

        def resolve_field(value: str | None, *, path: str) -> str:
            return _inline_field(inline_points, value, path=path)

        out: dict[str, Any] = {"type": "points", "points": inline_points}
    else:
        assert df is not None  # column mode implies a resolved source df
        lat = _field(df, layer.lat or layer.latitude, path=f"layers[{index}].lat")
        lng = _field(df, layer.lng or layer.lon or layer.longitude, path=f"layers[{index}].lng")
        if not _has_valid_point(df, lat, lng):
            raise MapSpecError(f"layers[{index}] has no valid latitude/longitude rows")
        out = {"type": "points", "source_id": layer.source_id, "lat": lat, "lng": lng}

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


def _normalize_geojson_layer(df: pd.DataFrame | None, layer: GeoJsonLayerSpec, index: int) -> dict[str, Any]:
    geojson = layer.geojson
    if isinstance(geojson, str):
        assert df is not None  # column mode implies a resolved source df
        geojson_value: object = _field(df, geojson, path=f"layers[{index}].geojson")
        if not _has_geojson_value(df, str(geojson_value)):
            raise MapSpecError(f"layers[{index}].geojson has no valid GeoJSON sample values")
    elif _is_geojson_object(geojson):
        geojson_value = copy.deepcopy(geojson)
    else:
        raise MapSpecError(f"layers[{index}].geojson must be a GeoJSON column or object")

    out: dict[str, Any] = {"type": "geojson", "geojson": geojson_value}
    if layer.source_id is not None:
        out["source_id"] = layer.source_id

    def resolve_field(value: str | None, *, path: str) -> str:
        assert df is not None
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


def parse_map_spec(spec: Mapping[str, object]) -> MapSpec:
    """Validate a raw map spec into a typed model, raising ``MapSpecError``."""
    try:
        return MapSpec.model_validate(spec)
    except ValidationError as e:
        raise MapSpecError(_validation_message(e)) from None


def referenced_source_ids(parsed: MapSpec) -> list[str]:
    """Return the distinct source ids referenced by a parsed spec, in order."""
    ids: list[str] = []
    for layer in parsed.layers:
        rid = getattr(layer, "source_id", None)
        if rid and rid not in ids:
            ids.append(rid)
    return ids


def normalize_map_spec(
    spec: MapSpec | Mapping[str, object],
    sources: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    """Validate and normalize a raw or parsed spec against source DataFrames.

    Each column/geojson layer is resolved against ``sources[layer.source_id]`` and
    tagged with its ``source`` id; inline layers need no source.
    """
    if isinstance(spec, MapSpec):
        parsed = spec
    else:
        parsed = parse_map_spec(spec)

    out: dict[str, Any] = {}
    if parsed.title is not None:
        out["title"] = copy.deepcopy(parsed.title)
    if parsed.view is not None:
        out["view"] = parsed.view.model_dump(exclude_none=True)

    layers: list[dict[str, Any]] = []
    for index, layer in enumerate(parsed.layers):
        rid = getattr(layer, "source_id", None)
        if rid is not None and rid not in sources:
            raise MapSpecError(f"layers[{index}] references unknown source_id {rid!r}")
        df = sources.get(rid) if rid is not None else None
        if isinstance(layer, PointsLayerSpec):
            layers.append(_normalize_points_layer(df, layer, index))
        elif isinstance(layer, GeoJsonLayerSpec):
            layers.append(_normalize_geojson_layer(df, layer, index))
        else:
            raise MapSpecError(f"layers[{index}].type must be 'points' or 'geojson'")
    out["layers"] = layers
    return out
