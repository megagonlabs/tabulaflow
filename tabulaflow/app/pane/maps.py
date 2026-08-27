"""Build structured map payloads for the browser output pane."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from tabulaflow.app.pane.contract import ColumnDesc, DatasetData, MapCardData, MapData


def _as_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _field_name(value: object, field_by_column: Mapping[str, str]) -> str | None:
    name = _as_str(value)
    if name is None:
        return None
    return field_by_column.get(name, name)


def _field_list(value: object, field_by_column: Mapping[str, str]) -> list[str] | bool | None:
    if value is True:
        return True
    if isinstance(value, str):
        field = _field_name(value, field_by_column)
        return [field] if field is not None else None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        fields: list[str] = []
        for item in value:
            field = _field_name(item, field_by_column)
            if field is not None:
                fields.append(field)
        return fields or None
    return None


def _field_encoding(value: object, field_by_column: Mapping[str, str]) -> object:
    if not isinstance(value, Mapping):
        return None
    out = {key: value[key] for key in ("field", "domain") if key in value}
    field = _field_name(out.get("field"), field_by_column)
    if field is None:
        return None
    out["field"] = field
    return out


def _literal_field_encoding(value: object) -> object:
    if not isinstance(value, Mapping):
        return None
    out = {key: value[key] for key in ("field", "domain") if key in value}
    return out if isinstance(out.get("field"), str) else None


def _normalize_points_layer(
    layer: Mapping[str, object],
    field_by_column: Mapping[str, str],
) -> dict[str, object] | None:
    inline_points = layer.get("points")
    if isinstance(inline_points, Sequence) and not isinstance(inline_points, (str, bytes, bytearray)):
        points = [dict(point) for point in inline_points if isinstance(point, Mapping)]
        if not points:
            return None
        inline_out: dict[str, object] = {"type": "points", "points": points}
        label = _as_str(layer.get("label"))
        if label is not None:
            inline_out["label"] = label
        tooltip = _field_list(layer.get("tooltip"), {})
        if tooltip is not None:
            inline_out["tooltip"] = tooltip
        marker = layer.get("marker")
        if isinstance(marker, Mapping):
            marker_type = marker.get("type")
            if marker_type in {"pin", "circle"}:
                inline_out["marker"] = {"type": marker_type}
        color = _literal_field_encoding(layer.get("color"))
        if color is not None:
            inline_out["color"] = color
        size = _literal_field_encoding(layer.get("size"))
        if size is not None:
            inline_out["size"] = size
        return inline_out

    lat = _field_name(layer.get("lat") or layer.get("latitude"), field_by_column)
    lng = _field_name(layer.get("lng") or layer.get("lon") or layer.get("longitude"), field_by_column)
    if lat is None or lng is None:
        return None

    out: dict[str, object] = {"type": "points", "lat": lat, "lng": lng}
    for key in ("label",):
        field = _field_name(layer.get(key), field_by_column)
        if field is not None:
            out[key] = field
    tooltip = _field_list(layer.get("tooltip"), field_by_column)
    if tooltip is not None:
        out["tooltip"] = tooltip
    marker = layer.get("marker")
    if isinstance(marker, Mapping):
        marker_type = marker.get("type")
        if marker_type in {"pin", "circle"}:
            out["marker"] = {"type": marker_type}
    color = _field_encoding(layer.get("color"), field_by_column)
    if color is not None:
        out["color"] = color
    size = _field_encoding(layer.get("size"), field_by_column)
    if size is not None:
        out["size"] = size
    return out


def _normalize_geojson_layer(
    layer: Mapping[str, object], field_by_column: Mapping[str, str]
) -> dict[str, object] | None:
    geojson = layer.get("geojson")
    if geojson is None:
        return None

    out: dict[str, object] = {"type": "geojson"}
    field = _field_name(geojson, field_by_column)
    out["geojson"] = field if field is not None else geojson
    for key in ("label",):
        field = _field_name(layer.get(key), field_by_column)
        if field is not None:
            out[key] = field
    tooltip = _field_list(layer.get("tooltip"), field_by_column)
    if tooltip is not None:
        out["tooltip"] = tooltip
    color = _field_encoding(layer.get("color"), field_by_column)
    if color is not None:
        out["color"] = color
    return out


def _normalize_layers(
    map_spec: Mapping[str, object],
    *,
    field_by_column_by_source: Mapping[str, Mapping[str, str]],
) -> list[dict[str, object]]:
    raw_layers = map_spec.get("layers")
    layers: list[dict[str, object]] = []
    if isinstance(raw_layers, Sequence) and not isinstance(raw_layers, (str, bytes, bytearray)):
        for raw_layer in raw_layers:
            if not isinstance(raw_layer, Mapping):
                continue
            source = _as_str(raw_layer.get("source_id"))
            field_by_column = field_by_column_by_source.get(source, {}) if source else {}
            layer_type = _as_str(raw_layer.get("type")) or "points"
            if layer_type == "points":
                layer = _normalize_points_layer(raw_layer, field_by_column)
            elif layer_type == "geojson":
                layer = _normalize_geojson_layer(raw_layer, field_by_column)
            else:
                layer = None
            if layer is not None:
                if source is not None:
                    layer["source"] = source
                layers.append(layer)
        return layers

    return []


def build_map_data(
    map_spec: Mapping[str, object],
    sources: Mapping[str, Mapping[str, object]],
) -> MapCardData | None:
    """Build a browser-pane map payload from a spec and its per-source datasets.

    Each column/geojson layer names the ``source_id`` it reads from; column
    references (using each source's original column names) are rewritten to that
    source's compact pane field names, and the source datasets are bundled so the
    browser reads ``datasets[layer.source].rows`` per layer.

    Args:
        map_spec: Normalized map configuration whose layers carry a
            ``source_id``, with a non-empty ``layers`` list.
        sources: Mapping from source id to a dataset dict with ``rows``,
            ``columns``, and ``field_by_column`` (original column name → pane
            field name).

    Returns:
        A ``{"map": ..., "datasets": ...}`` payload, or ``None`` when no valid
        layer can be resolved.
    """
    field_by_column_by_source: dict[str, Mapping[str, str]] = {}
    for rid, source in sources.items():
        fbc = source.get("field_by_column", {})
        if isinstance(fbc, Mapping):
            field_by_column_by_source[rid] = {str(k): str(v) for k, v in fbc.items()}
    layers = _normalize_layers(map_spec, field_by_column_by_source=field_by_column_by_source)
    if not layers:
        return None

    out: MapData = {
        "provider": "maplibre",
        "layers": layers,
    }
    view = map_spec.get("view")
    if isinstance(view, Mapping):
        out["view"] = dict(view)
    datasets: dict[str, DatasetData] = {}
    for rid, source in sources.items():
        rows = source.get("rows", [])
        columns = source.get("columns", [])
        datasets[rid] = {
            "rows": cast(list[dict[str, object]], rows if isinstance(rows, list) else []),
            "columns": cast(list[ColumnDesc], columns if isinstance(columns, list) else []),
        }
    return {"map": out, "datasets": datasets}
