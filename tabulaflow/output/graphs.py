"""Graph specification parsing, normalization, and materialization."""

from __future__ import annotations

import copy
import numbers
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from tabulaflow.core.results import GraphResult, GraphResultEdge, GraphResultNode
from tabulaflow.core.serialization import json_ready
from tabulaflow.output.specs import ArtifactSpecError


def _resolve_column(df: pd.DataFrame, name: str) -> str | None:
    matches = [str(column) for column in df.columns if str(column).casefold() == name.casefold()]
    return matches[0] if len(matches) == 1 else None


GRAPH_MAX_NODES = 300
GRAPH_MAX_EDGES = 700

__all__ = [
    "GRAPH_MAX_EDGES",
    "GRAPH_MAX_NODES",
    "GraphEdgeSourceSpec",
    "GraphLiteralValueSpec",
    "GraphNodeSourceSpec",
    "GraphSize",
    "GraphSpec",
    "GraphSpecError",
    "graph_size",
    "materialize_graph_result",
    "normalize_graph_spec",
    "parse_graph_spec",
    "referenced_source_ids",
    "validate_graph_size",
]


class GraphSpecError(ArtifactSpecError):
    """Raised when a graph spec cannot be applied to a result."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GraphLiteralValueSpec(_StrictModel):
    """Literal label or group value in a graph source."""

    value: str


class _GraphSourceBase(_StrictModel):
    source_id: str | None = None
    data: list[dict[str, Any]] | None = None

    @model_validator(mode="after")
    def _validate_source_mode(self) -> _GraphSourceBase:
        has_source_id = self.source_id is not None
        has_data = self.data is not None
        if has_source_id == has_data:
            raise ValueError("graph sources must set exactly one of source_id or data")
        if self.data is not None and not self.data:
            raise ValueError("inline graph data must be a non-empty list")
        return self


class GraphNodeSourceSpec(_GraphSourceBase):
    """Node source backed by columns or inline rows."""

    id: str
    label: str | None = None
    group: str | GraphLiteralValueSpec | None = None
    tooltip: str | list[str] | Literal[True] | None = None


class GraphEdgeSourceSpec(_GraphSourceBase):
    """Edge source backed by columns or inline rows."""

    source: str
    target: str
    label: str | GraphLiteralValueSpec | None = None
    directed: bool = True
    tooltip: str | list[str] | Literal[True] | None = None


class GraphSpec(_StrictModel):
    """Declarative node-link graph specification."""

    title: str | None = None
    layout: Literal["force", "layered", "tree"] = "force"
    nodes: list[GraphNodeSourceSpec] = Field(min_length=1)
    edges: list[GraphEdgeSourceSpec] = Field(default_factory=list)


@dataclass(frozen=True)
class GraphSize:
    """Final materialized graph size and node typing counts."""

    nodes: int
    edges: int
    groups: int
    ungrouped_nodes: int


def _validation_message(error: ValidationError) -> str:
    errors = error.errors()
    unsupported_top_level: list[str] = []
    for item in errors:
        loc = item.get("loc", ())
        if item.get("type") == "extra_forbidden" and len(loc) == 1:
            unsupported_top_level.append(str(loc[0]))
    unsupported_top_level.sort()
    if unsupported_top_level:
        return f"unsupported graph_spec field(s): {unsupported_top_level}"
    if errors:
        first = errors[0]
        ctx_error = first.get("ctx", {}).get("error")
        if ctx_error is not None:
            return str(ctx_error)
        loc_text = ".".join(str(part) for part in first.get("loc", ()))
        msg = str(first.get("msg", "invalid graph_spec"))
        return f"{loc_text}: {msg}" if loc_text else msg
    return "invalid graph_spec"


def _field(df: pd.DataFrame, value: str | None, *, path: str) -> str:
    if not value:
        raise GraphSpecError(f"{path} must be a column name")
    resolved = _resolve_column(df, value)
    if resolved is None:
        raise GraphSpecError(f"field not found: {value!r}. Available columns: {list(df.columns)}")
    return resolved


def _inline_field(rows: Sequence[Mapping[str, object]], value: str | None, *, path: str) -> str:
    if not value:
        raise GraphSpecError(f"{path} must be an inline property name")
    if not any(value in row for row in rows):
        raise GraphSpecError(f"inline property not found: {value!r}")
    return value


def _optional_field(resolve_field: Callable[..., str], value: str | None, *, path: str) -> str | None:
    if value is None:
        return None
    return resolve_field(value, path=path)


def _field_or_value(
    resolve_field: Callable[..., str], value: str | GraphLiteralValueSpec | None, *, path: str
) -> str | dict[str, str] | None:
    if isinstance(value, GraphLiteralValueSpec):
        if not value.value:
            raise GraphSpecError(f"{path}.value must be a non-empty string")
        return {"value": value.value}
    return _optional_field(resolve_field, value, path=path)


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


def _normalize_node_source(df: pd.DataFrame | None, source: GraphNodeSourceSpec, index: int) -> dict[str, Any]:
    if source.data is not None:
        rows = source.data

        def resolve_field(value: str | None, *, path: str) -> str:
            return _inline_field(rows, value, path=path)

        out: dict[str, Any] = {"data": copy.deepcopy(rows), "id": resolve_field(source.id, path=f"nodes[{index}].id")}
    else:
        assert df is not None

        def resolve_field(value: str | None, *, path: str) -> str:
            return _field(df, value, path=path)

        out = {"source_id": source.source_id, "id": resolve_field(source.id, path=f"nodes[{index}].id")}

    label = _optional_field(resolve_field, source.label, path=f"nodes[{index}].label")
    if label is not None:
        out["label"] = label
    group = _field_or_value(resolve_field, source.group, path=f"nodes[{index}].group")
    if group is not None:
        out["group"] = group
    tooltip = _tooltip(resolve_field, source.tooltip, path=f"nodes[{index}].tooltip")
    if tooltip is not None:
        out["tooltip"] = tooltip
    return out


def _normalize_edge_source(df: pd.DataFrame | None, source: GraphEdgeSourceSpec, index: int) -> dict[str, Any]:
    if source.data is not None:
        rows = source.data

        def resolve_field(value: str | None, *, path: str) -> str:
            return _inline_field(rows, value, path=path)

        out: dict[str, Any] = {
            "data": copy.deepcopy(rows),
            "source": resolve_field(source.source, path=f"edges[{index}].source"),
            "target": resolve_field(source.target, path=f"edges[{index}].target"),
        }
    else:
        assert df is not None

        def resolve_field(value: str | None, *, path: str) -> str:
            return _field(df, value, path=path)

        out = {
            "source_id": source.source_id,
            "source": resolve_field(source.source, path=f"edges[{index}].source"),
            "target": resolve_field(source.target, path=f"edges[{index}].target"),
        }

    label = _field_or_value(resolve_field, source.label, path=f"edges[{index}].label")
    if label is not None:
        out["label"] = label
    out["directed"] = source.directed
    tooltip = _tooltip(resolve_field, source.tooltip, path=f"edges[{index}].tooltip")
    if tooltip is not None:
        out["tooltip"] = tooltip
    return out


def parse_graph_spec(spec: Mapping[str, object]) -> GraphSpec:
    """Validate a raw graph spec into a typed model, raising ``GraphSpecError``."""
    try:
        return GraphSpec.model_validate(spec)
    except ValidationError as e:
        raise GraphSpecError(_validation_message(e)) from None


def referenced_source_ids(parsed: GraphSpec) -> list[str]:
    """Return the distinct output-store source ids referenced by a parsed spec."""
    ids: list[str] = []
    all_sources: list[GraphNodeSourceSpec | GraphEdgeSourceSpec] = [
        *parsed.nodes,
        *parsed.edges,
    ]
    for source in all_sources:
        rid = source.source_id
        if rid and rid not in ids:
            ids.append(rid)
    return ids


def normalize_graph_spec(
    spec: GraphSpec | Mapping[str, object],
    sources: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    """Validate and normalize a raw or parsed spec against source DataFrames."""
    parsed = spec if isinstance(spec, GraphSpec) else parse_graph_spec(spec)
    out: dict[str, Any] = {"layout": parsed.layout}
    if parsed.title is not None:
        out["title"] = parsed.title

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for index, node_source in enumerate(parsed.nodes):
        df = sources.get(node_source.source_id) if node_source.source_id is not None else None
        if node_source.source_id is not None and df is None:
            raise GraphSpecError(f"nodes[{index}] references unknown source_id {node_source.source_id!r}")
        nodes.append(_normalize_node_source(df, node_source, index))
    for index, edge_source in enumerate(parsed.edges):
        df = sources.get(edge_source.source_id) if edge_source.source_id is not None else None
        if edge_source.source_id is not None and df is None:
            raise GraphSpecError(f"edges[{index}] references unknown source_id {edge_source.source_id!r}")
        edges.append(_normalize_edge_source(df, edge_source, index))

    out["nodes"] = nodes
    out["edges"] = edges
    return out


def _source_rows(source: Mapping[str, object], sources: Mapping[str, pd.DataFrame]) -> list[Mapping[str, object]]:
    inline = source.get("data")
    if isinstance(inline, Sequence) and not isinstance(inline, str | bytes | bytearray):
        return [row for row in inline if isinstance(row, Mapping)]
    rid = source.get("source_id")
    if not isinstance(rid, str) or rid not in sources:
        return []
    return [row for row in sources[rid].to_dict(orient="records") if isinstance(row, Mapping)]


def _row_value(row: Mapping[str, object], field: object) -> object:
    return row.get(field) if isinstance(field, str) else None


def _node_id(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _safe_graph_property(value: object, *, depth: int = 0) -> object:
    if value is None or isinstance(value, (str, bool, numbers.Integral, numbers.Real)):
        return json_ready(value)
    if depth >= 4:
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _safe_graph_property(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_safe_graph_property(item, depth=depth + 1) for item in value]
    return str(value)


def _constant_value(value: object) -> object:
    return value.get("value") if isinstance(value, Mapping) else None


def _properties(
    row: Mapping[str, object],
    tooltip: object,
) -> dict[str, object]:
    if tooltip is None:
        return {}
    if tooltip is True:
        fields = [str(key) for key in row.keys()]
    elif isinstance(tooltip, str):
        fields = [tooltip]
    elif isinstance(tooltip, Sequence) and not isinstance(tooltip, (str, bytes, bytearray)):
        fields = [str(item) for item in tooltip if isinstance(item, str)]
    else:
        fields = []
    return {field: _safe_graph_property(row[field]) for field in fields if field in row}


def materialize_graph_result(graph_spec: Mapping[str, object], sources: Mapping[str, pd.DataFrame]) -> GraphResult:
    """Materialize a normalized graph spec into the typed graph-view data contract."""
    nodes_by_id: dict[str, GraphResultNode] = {}
    node_rows_seen = 0
    raw_nodes = graph_spec.get("nodes")
    for raw_source in raw_nodes if isinstance(raw_nodes, list) else []:
        if not isinstance(raw_source, Mapping):
            continue
        id_field = raw_source.get("id")
        label_field = raw_source.get("label")
        group_field = raw_source.get("group")
        constant_group = _constant_value(group_field)
        for row in _source_rows(raw_source, sources):
            node_rows_seen += 1
            node_id = _node_id(_row_value(row, id_field))
            if node_id is None or node_id in nodes_by_id:
                continue
            label = _row_value(row, label_field) if isinstance(label_field, str) else None
            group = constant_group if constant_group is not None else _row_value(row, group_field)
            properties = _properties(row, raw_source.get("tooltip"))
            nodes_by_id[node_id] = GraphResultNode(
                id=node_id,
                label=str(label) if label is not None else None,
                group=str(group) if group is not None else None,
                properties=properties,
            )

    edges: list[GraphResultEdge] = []
    unmatched: set[str] = set()
    raw_edges = graph_spec.get("edges")
    for raw_source in raw_edges if isinstance(raw_edges, list) else []:
        if not isinstance(raw_source, Mapping):
            continue
        source_field = raw_source.get("source")
        target_field = raw_source.get("target")
        label_field = raw_source.get("label")
        constant_label = _constant_value(label_field)
        directed = bool(raw_source.get("directed", True))
        for row in _source_rows(raw_source, sources):
            source_id = _node_id(_row_value(row, source_field))
            target_id = _node_id(_row_value(row, target_field))
            if source_id is None or target_id is None:
                continue
            for node_id in (source_id, target_id):
                if node_id not in nodes_by_id:
                    unmatched.add(node_id)
            label = constant_label if constant_label is not None else _row_value(row, label_field)
            properties = _properties(row, raw_source.get("tooltip"))
            edges.append(
                GraphResultEdge(
                    source=source_id,
                    target=target_id,
                    directed=directed,
                    label=str(label) if label is not None else None,
                    properties=properties,
                )
            )

    if unmatched:
        sample = ", ".join(repr(node_id) for node_id in sorted(unmatched)[:5])
        raise GraphSpecError(
            f"{len(unmatched)} edge endpoint id(s) match no node source id (e.g. {sample}); "
            "declare a node source covering every endpoint column"
        )

    if not nodes_by_id and node_rows_seen:
        raise GraphSpecError("graph has no valid nodes")

    return GraphResult(
        nodes=sorted(nodes_by_id.values(), key=lambda node: node.id),
        edges=edges,
    )


def graph_size(graph: GraphResult) -> GraphSize:
    """Return node, edge, and node-group counts for a materialized graph."""
    groups = {node.group for node in graph.nodes if node.group is not None}
    ungrouped = sum(1 for node in graph.nodes if node.group is None)
    return GraphSize(nodes=len(graph.nodes), edges=len(graph.edges), groups=len(groups), ungrouped_nodes=ungrouped)


def validate_graph_size(size: GraphSize) -> None:
    """Reject graph payloads that are too large for an interactive node-link view."""
    if size.nodes > GRAPH_MAX_NODES:
        raise GraphSpecError(
            f"graph has {size.nodes:,} nodes — too large to render directly; filter, aggregate, or take top-N first; "
            f"max {GRAPH_MAX_NODES:,} nodes"
        )
    if size.edges > GRAPH_MAX_EDGES:
        raise GraphSpecError(
            f"graph has {size.edges:,} edges — too large to render directly; filter, aggregate, or take top-N first; "
            f"max {GRAPH_MAX_EDGES:,} edges"
        )
