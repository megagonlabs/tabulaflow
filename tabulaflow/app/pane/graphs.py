"""Build structured graph payloads for the browser output pane."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from tabulaflow.app.pane.types import GraphCardData
from tabulaflow.toolhub.render_graph import GRAPH_MAX_EDGES, GRAPH_MAX_NODES

_DEFAULT_NODE_COLOR = "#3eb489"
_PALETTE = [
    "#3eb489",
    "#5ac8fa",
    "#f5a623",
    "#bd6cf0",
    "#f06292",
    "#4dd0e1",
    "#aed581",
    "#ff8a65",
]


def _as_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _field_name(value: object, field_by_column: Mapping[str, str]) -> str | None:
    name = _as_str(value)
    if name is None:
        return None
    return field_by_column.get(name, name)


def _rows_for(
    source: Mapping[str, object], sources: Mapping[str, Mapping[str, object]]
) -> tuple[list[dict[str, object]], Mapping[str, str]]:
    inline = source.get("data")
    if isinstance(inline, Sequence) and not isinstance(inline, (str, bytes, bytearray)):
        rows = [dict(row) for row in inline if isinstance(row, Mapping)]
        return rows, {}

    rid = _as_str(source.get("record_id"))
    if rid is None:
        return [], {}
    payload = sources.get(rid, {})
    rows_obj = payload.get("rows", [])
    rows = cast(list[dict[str, object]], rows_obj if isinstance(rows_obj, list) else [])
    fbc = payload.get("field_by_column", {})
    field_by_column = {str(k): str(v) for k, v in fbc.items()} if isinstance(fbc, Mapping) else {}
    return rows, field_by_column


def _tooltip(
    row: Mapping[str, object],
    tooltip: object,
    field_by_column: Mapping[str, str],
) -> dict[str, object] | None:
    if tooltip is None:
        return None
    if tooltip is True:
        fields = [str(key) for key in row.keys()]
    elif isinstance(tooltip, str):
        field = _field_name(tooltip, field_by_column)
        fields = [field] if field is not None else []
    elif isinstance(tooltip, Sequence) and not isinstance(tooltip, (str, bytes, bytearray)):
        fields = [field for item in tooltip if (field := _field_name(item, field_by_column)) is not None]
    else:
        fields = []

    out: dict[str, object] = {}
    reverse = {field: column for column, field in field_by_column.items()}
    for field in fields:
        if field not in row:
            continue
        value = row[field]
        if value is None or isinstance(value, str | int | float | bool):
            out[reverse.get(field, field)] = value
    return out or None


def _assign_colors(nodes: list[dict[str, object]]) -> None:
    groups = sorted({str(node["group"]) for node in nodes if node.get("group") is not None})
    color_by_group = {group: _PALETTE[index % len(_PALETTE)] for index, group in enumerate(groups)}
    for node in nodes:
        group = node.get("group")
        node["color"] = (
            color_by_group.get(str(group), _DEFAULT_NODE_COLOR) if group is not None else _DEFAULT_NODE_COLOR
        )


def _edge_id(index: int, node_ids: set[str]) -> str:
    edge_id = f"__tf_edge_{index}"
    while edge_id in node_ids:
        edge_id = f"_{edge_id}"
    return edge_id


def build_graph_data(
    graph_spec: Mapping[str, object],
    sources: Mapping[str, Mapping[str, object]],
) -> GraphCardData | None:
    """Build a browser-pane graph payload from a spec and per-source datasets."""
    nodes_by_id: dict[str, dict[str, object]] = {}

    raw_node_sources = graph_spec.get("nodes", [])
    if isinstance(raw_node_sources, Sequence) and not isinstance(raw_node_sources, (str, bytes, bytearray)):
        for raw_source in raw_node_sources:
            if not isinstance(raw_source, Mapping):
                continue
            rows, field_by_column = _rows_for(raw_source, sources)
            id_field = _field_name(raw_source.get("id"), field_by_column)
            if id_field is None:
                continue
            label_field = _field_name(raw_source.get("label"), field_by_column)
            group_field = _field_name(raw_source.get("group"), field_by_column)
            for row in rows:
                node_id = _as_str(row.get(id_field))
                if node_id is None or node_id in nodes_by_id:
                    continue
                node: dict[str, object] = {
                    "id": node_id,
                    "label": _as_str(row.get(label_field)) if label_field else node_id,
                }
                if group_field and row.get(group_field) is not None:
                    node["group"] = str(row[group_field])
                tooltip = _tooltip(row, raw_source.get("tooltip"), field_by_column)
                if tooltip is not None:
                    node["tooltip"] = tooltip
                nodes_by_id[node_id] = node

    edges: list[dict[str, object]] = []
    unmatched_nodes = 0
    raw_edge_sources = graph_spec.get("edges", [])
    if isinstance(raw_edge_sources, Sequence) and not isinstance(raw_edge_sources, (str, bytes, bytearray)):
        for raw_source in raw_edge_sources:
            if not isinstance(raw_source, Mapping):
                continue
            rows, field_by_column = _rows_for(raw_source, sources)
            source_field = _field_name(raw_source.get("source"), field_by_column)
            target_field = _field_name(raw_source.get("target"), field_by_column)
            if source_field is None or target_field is None:
                continue
            label_field = _field_name(raw_source.get("label"), field_by_column)
            directed = bool(raw_source.get("directed", True))
            for row in rows:
                source_id = _as_str(row.get(source_field))
                target_id = _as_str(row.get(target_field))
                if source_id is None or target_id is None:
                    continue
                for node_id in (source_id, target_id):
                    if node_id not in nodes_by_id:
                        nodes_by_id[node_id] = {"id": node_id, "label": node_id}
                        unmatched_nodes += 1
                edge: dict[str, object] = {
                    "source": source_id,
                    "target": target_id,
                }
                if directed:
                    edge["directed"] = True
                if label_field and row.get(label_field) is not None:
                    edge["label"] = str(row[label_field])
                tooltip = _tooltip(row, raw_source.get("tooltip"), field_by_column)
                if tooltip is not None:
                    edge["tooltip"] = tooltip
                edges.append(edge)

    if not edges:
        return None
    if len(nodes_by_id) > GRAPH_MAX_NODES or len(edges) > GRAPH_MAX_EDGES:
        return None

    node_payloads = sorted(nodes_by_id.values(), key=lambda node: str(node["id"]))
    _assign_colors(node_payloads)
    node_ids = {str(node["id"]) for node in node_payloads}

    edge_payloads = sorted(
        edges,
        key=lambda edge: (
            str(edge.get("source", "")),
            str(edge.get("target", "")),
            str(edge.get("label", "")),
            str(edge.get("directed", "")),
        ),
    )
    for index, edge in enumerate(edge_payloads, start=1):
        edge["id"] = _edge_id(index, node_ids)

    raw_layout = graph_spec.get("layout")
    layout = raw_layout if isinstance(raw_layout, str) and raw_layout in {"force", "layered", "tree"} else "force"
    return cast(
        GraphCardData,
        {
            "graph": {
                "layout": layout,
                "elements": {
                    "nodes": [{"data": node} for node in node_payloads],
                    "edges": [{"data": edge} for edge in edge_payloads],
                },
                "meta": {"unmatchedNodes": unmatched_nodes},
            }
        },
    )
