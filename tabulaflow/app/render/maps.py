"""Build structured Leaflet map payloads for the browser output pane."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"


def _as_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _field_name(value: object, field_by_column: Mapping[str, str]) -> str | None:
    name = _as_str(value)
    if name is None:
        return None
    return field_by_column.get(name, name)


def _first_field(candidates: list[object], field_by_column: Mapping[str, str]) -> str | None:
    for candidate in candidates:
        field = _field_name(candidate, field_by_column)
        if field is not None:
            return field
    return None


def _column_named(df: pd.DataFrame, names: set[str]) -> str | None:
    for column in df.columns:
        if str(column).strip().lower() in names:
            return str(column)
    return None


def build_map_data(
    df: pd.DataFrame,
    map_spec: Mapping[str, object],
    *,
    field_by_column: Mapping[str, str],
) -> dict[str, object] | None:
    """Build a browser-pane map payload from a DataFrame and declarative spec.

    Args:
        df: DataFrame backing the output-pane record.
        map_spec: Declarative map configuration. ``lat`` and ``lng`` can refer
            to the DataFrame's original column names; they are rewritten to the
            pane dataset's compact field names.
        field_by_column: Mapping from original DataFrame column names to pane
            dataset field names.

    Returns:
        A ``{"map": ...}`` payload, or ``None`` when no latitude/longitude
        fields can be resolved.
    """
    lat = _first_field(
        [
            map_spec.get("lat"),
            map_spec.get("latitude"),
            _column_named(df, {"lat", "latitude"}),
        ],
        field_by_column,
    )
    lng = _first_field(
        [
            map_spec.get("lng"),
            map_spec.get("lon"),
            map_spec.get("longitude"),
            _column_named(df, {"lng", "lon", "longitude"}),
        ],
        field_by_column,
    )
    if lat is None or lng is None:
        return None

    out: dict[str, object] = {
        "provider": "leaflet",
        "tileUrl": _as_str(map_spec.get("tileUrl")) or _as_str(map_spec.get("tile_url")) or OSM_TILE_URL,
        "attribution": _as_str(map_spec.get("attribution")) or OSM_ATTRIBUTION,
        "lat": lat,
        "lng": lng,
    }
    for key in ("label", "tooltip"):
        field = _field_name(map_spec.get(key), field_by_column)
        if field is not None:
            out[key] = field
    for key in ("center", "zoom", "maxZoom", "marker"):
        value = map_spec.get(key)
        if value is not None:
            out[key] = value
    return {"map": out}
