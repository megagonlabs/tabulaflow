"""Build structured graph payloads for the browser output pane."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tabulaflow.app.pane.contract import GraphCardData
from tabulaflow.output.graphs import GRAPH_MAX_EDGES, GRAPH_MAX_NODES


def _as_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _edge_id(index: int, node_ids: set[str]) -> str:
    edge_id = f"__tf_edge_{index}"
    while edge_id in node_ids:
        edge_id = f"_{edge_id}"
    return edge_id


def _graph_card_data_from_rows(
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    *,
    layout: str = "force",
    group_domain: list[str] | None = None,
) -> GraphCardData | None:
    if len(nodes) > GRAPH_MAX_NODES or len(edges) > GRAPH_MAX_EDGES:
        return None

    node_payloads = sorted((dict(node) for node in nodes), key=lambda node: str(node.get("id", "")))
    node_ids = {str(node["id"]) for node in node_payloads if node.get("id") is not None}

    edge_payloads = sorted(
        (dict(edge) for edge in edges),
        key=lambda edge: (
            str(edge.get("source", "")),
            str(edge.get("target", "")),
            str(edge.get("label", "")),
            str(edge.get("directed", "")),
        ),
    )
    used_ids = set(node_ids)
    for index, edge in enumerate(edge_payloads, start=1):
        if edge.get("directed") is False:
            edge.pop("directed")
        edge_id = _as_str(edge.get("id")) or _edge_id(index, used_ids)
        while edge_id in used_ids:
            edge_id = f"_{edge_id}"
        edge["id"] = edge_id
        used_ids.add(edge_id)

    graph_data: dict[str, object] = {
        "layout": layout,
        "elements": {
            "nodes": [{"data": node} for node in node_payloads],
            "edges": [{"data": edge} for edge in edge_payloads],
        },
    }
    if group_domain is not None:
        graph_data["groupDomain"] = list(group_domain)
    return cast(
        GraphCardData,
        {"graph": graph_data},
    )


def build_graph_result_data(graph_result: object, group_domain: list[str] | None = None) -> GraphCardData | None:
    """Build a browser-pane graph payload from a materialized graph view."""
    nodes = getattr(graph_result, "nodes", None)
    edges = getattr(graph_result, "edges", None)
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return None

    def to_row(value: object) -> dict[str, object] | None:
        if isinstance(value, Mapping):
            return dict(value)
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(exclude_none=True)
            return dict(dumped) if isinstance(dumped, Mapping) else None
        return None

    node_rows = [row for node in nodes if (row := to_row(node)) is not None]
    edge_rows = [row for edge in edges if (row := to_row(edge)) is not None]
    return _graph_card_data_from_rows(node_rows, edge_rows, group_domain=group_domain)
