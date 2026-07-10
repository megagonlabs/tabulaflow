"""Tool that stores a declarative node-link graph artifact."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from pydantic_ai import Tool

from tabulaflow.toolhub.query_history import QueryHistory
from tabulaflow.toolhub.render_map import resolve_column

GRAPH_MAX_NODES = 300
GRAPH_MAX_EDGES = 700


class GraphSpecError(ValueError):
    """Raised when a graph spec cannot be applied to a result."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _SourceModel(_StrictModel):
    record_id: str | None = None
    data: list[dict[str, Any]] | None = None

    @model_validator(mode="after")
    def _validate_source_mode(self) -> _SourceModel:
        has_record = self.record_id is not None
        has_data = self.data is not None
        if has_record == has_data:
            raise ValueError("graph sources must set exactly one of record_id or data")
        if self.data is not None and not self.data:
            raise ValueError("inline graph data must be a non-empty list")
        return self


class _NodeSource(_SourceModel):
    id: str
    label: str | None = None
    group: str | None = None
    tooltip: str | list[str] | Literal[True] | None = None


class _EdgeSource(_SourceModel):
    source: str
    target: str
    label: str | None = None
    directed: bool = True
    tooltip: str | list[str] | Literal[True] | None = None


class _SubgraphSource(_StrictModel):
    record_id: str
    caption: str | None = None


class _GraphSpec(_StrictModel):
    title: str | None = None
    layout: Literal["force", "layered", "tree"] = "force"
    nodes: list[_NodeSource] = []
    edges: list[_EdgeSource] = []
    subgraph: list[_SubgraphSource] = []

    @model_validator(mode="after")
    def _require_edges(self) -> _GraphSpec:
        if not self.edges and not self.subgraph:
            raise ValueError("graph_spec must include at least one edge-bearing source")
        return self


@dataclass(frozen=True)
class GraphSize:
    """Final materialized graph size."""

    nodes: int
    edges: int


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
    resolved = resolve_column(df, value)
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


def _normalize_node_source(df: pd.DataFrame | None, source: _NodeSource, index: int) -> dict[str, Any]:
    if source.data is not None:
        rows = source.data

        def resolve_field(value: str | None, *, path: str) -> str:
            return _inline_field(rows, value, path=path)

        out: dict[str, Any] = {"data": copy.deepcopy(rows), "id": resolve_field(source.id, path=f"nodes[{index}].id")}
    else:
        assert df is not None

        def resolve_field(value: str | None, *, path: str) -> str:
            return _field(df, value, path=path)

        out = {"record_id": source.record_id, "id": resolve_field(source.id, path=f"nodes[{index}].id")}

    for key in ("label", "group"):
        field = _optional_field(resolve_field, getattr(source, key), path=f"nodes[{index}].{key}")
        if field is not None:
            out[key] = field
    tooltip = _tooltip(resolve_field, source.tooltip, path=f"nodes[{index}].tooltip")
    if tooltip is not None:
        out["tooltip"] = tooltip
    return out


def _normalize_edge_source(df: pd.DataFrame | None, source: _EdgeSource, index: int) -> dict[str, Any]:
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
            "record_id": source.record_id,
            "source": resolve_field(source.source, path=f"edges[{index}].source"),
            "target": resolve_field(source.target, path=f"edges[{index}].target"),
        }

    label = _optional_field(resolve_field, source.label, path=f"edges[{index}].label")
    if label is not None:
        out["label"] = label
    out["directed"] = source.directed
    tooltip = _tooltip(resolve_field, source.tooltip, path=f"edges[{index}].tooltip")
    if tooltip is not None:
        out["tooltip"] = tooltip
    return out


def _safe_scalar(value: object) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _graph_property_value(value: object, *, depth: int = 0) -> object:
    if _safe_scalar(value):
        return value
    if depth >= 4:
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _graph_property_value(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_graph_property_value(item, depth=depth + 1) for item in value]
    return str(value)


def _neo4j_node_id(node: object) -> str:
    element_id = getattr(node, "element_id", None)
    if element_id is not None:
        return str(element_id)
    return str(getattr(node, "id", node))


def _neo4j_node_label(node: object, caption: str | None) -> str:
    if caption and hasattr(node, "get"):
        value = node.get(caption)
        if value is not None:
            return str(value)
    for key in ("name", "title"):
        if hasattr(node, "get"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return value
    if hasattr(node, "items"):
        for _, value in node.items():
            if isinstance(value, str) and value.strip():
                return value
    return _neo4j_node_id(node)


def _neo4j_node_group(node: object) -> str:
    labels = sorted(str(label) for label in getattr(node, "labels", []) or [])
    return ":".join(labels) if labels else "node"


def _is_neo4j_node(value: object) -> bool:
    return (
        hasattr(value, "labels") and hasattr(value, "items") and (hasattr(value, "element_id") or hasattr(value, "id"))
    )


def _relationship_endpoints(rel: object) -> tuple[object, object] | None:
    start = getattr(rel, "start_node", None)
    end = getattr(rel, "end_node", None)
    if start is not None and end is not None:
        return start, end

    rel_nodes = getattr(rel, "nodes", None)
    if rel_nodes is None:
        return None
    try:
        if len(rel_nodes) < 2:
            return None
        start, end = rel_nodes[0], rel_nodes[1]
    except (TypeError, IndexError, KeyError):
        return None
    if start is None or end is None:
        return None
    return start, end


def _is_neo4j_relationship(value: object) -> bool:
    return (
        _relationship_endpoints(value) is not None
        and hasattr(value, "items")
        and (hasattr(value, "type") or hasattr(value, "element_id") or hasattr(value, "id"))
    )


def _is_neo4j_path(value: object) -> bool:
    return hasattr(value, "nodes") and hasattr(value, "relationships")


def _extract_subgraph_source(
    df: pd.DataFrame, source: _SubgraphSource, index: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    def add_node(node: object) -> str:
        node_id = _neo4j_node_id(node)
        if node_id in nodes:
            return node_id
        data: dict[str, Any] = {
            "id": node_id,
            "label": _neo4j_node_label(node, source.caption),
            "group": _neo4j_node_group(node),
        }
        if hasattr(node, "items"):
            for key, value in node.items():
                if key not in data:
                    data[str(key)] = _graph_property_value(value)
        nodes[node_id] = data
        return node_id

    def add_relationship(rel: object) -> None:
        endpoints = _relationship_endpoints(rel)
        if endpoints is None:
            return
        start, end = endpoints
        source_id = add_node(start)
        target_id = add_node(end)
        rel_id = getattr(rel, "element_id", None) or getattr(rel, "id", None)
        edge_id = str(rel_id) if rel_id is not None else f"{source_id}->{target_id}:{len(edges) + 1}"
        if edge_id in edges:
            return
        label = getattr(rel, "type", None) or type(rel).__name__
        data: dict[str, Any] = {
            "id": edge_id,
            "source": source_id,
            "target": target_id,
            "label": str(label),
        }
        if hasattr(rel, "items"):
            for key, value in rel.items():
                if key not in data:
                    data[str(key)] = _graph_property_value(value)
        edges[edge_id] = data

    def walk(value: object) -> None:
        if value is None:
            return
        if _is_neo4j_node(value):
            add_node(value)
            return
        if _is_neo4j_relationship(value):
            add_relationship(value)
            return
        if _is_neo4j_path(value):
            path_nodes = getattr(value, "nodes")
            path_relationships = getattr(value, "relationships")
            for node in path_nodes:
                add_node(node)
            for rel in path_relationships:
                add_relationship(rel)
            return
        if isinstance(value, Mapping):
            for item in value.values():
                walk(item)
            return
        if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            for item in value:
                walk(item)

    for _, row in df.iterrows():
        for value in row:
            walk(value)

    if edges:
        return list(nodes.values()), list(edges.values())
    raise GraphSpecError(f"subgraph[{index}] did not contain any Neo4j relationships or paths")


def parse_graph_spec(spec: Mapping[str, object]) -> _GraphSpec:
    """Validate a raw graph spec into a typed model, raising ``GraphSpecError``."""
    try:
        return _GraphSpec.model_validate(spec)
    except ValidationError as e:
        raise GraphSpecError(_validation_message(e)) from None


def referenced_record_ids(parsed: _GraphSpec) -> list[str]:
    """Return the distinct query-history record ids referenced by a parsed spec."""
    ids: list[str] = []
    all_sources: list[_NodeSource | _EdgeSource | _SubgraphSource] = [
        *parsed.nodes,
        *parsed.edges,
        *parsed.subgraph,
    ]
    for source in all_sources:
        rid = source.record_id
        if rid and rid not in ids:
            ids.append(rid)
    return ids


def resolve_graph_spec(parsed: _GraphSpec, sources: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    """Resolve a parsed spec against per-source DataFrames."""
    out: dict[str, Any] = {"layout": parsed.layout}
    if parsed.title is not None:
        out["title"] = parsed.title

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for index, node_source in enumerate(parsed.nodes):
        df = sources.get(node_source.record_id) if node_source.record_id is not None else None
        if node_source.record_id is not None and df is None:
            raise GraphSpecError(f"nodes[{index}] references unknown record_id {node_source.record_id!r}")
        nodes.append(_normalize_node_source(df, node_source, index))
    for index, edge_source in enumerate(parsed.edges):
        df = sources.get(edge_source.record_id) if edge_source.record_id is not None else None
        if edge_source.record_id is not None and df is None:
            raise GraphSpecError(f"edges[{index}] references unknown record_id {edge_source.record_id!r}")
        edges.append(_normalize_edge_source(df, edge_source, index))
    for index, sub_source in enumerate(parsed.subgraph):
        df = sources.get(sub_source.record_id)
        if df is None:
            raise GraphSpecError(f"subgraph[{index}] references unknown record_id {sub_source.record_id!r}")
        sub_nodes, sub_edges = _extract_subgraph_source(df, sub_source, index)
        nodes.append({"data": sub_nodes, "id": "id", "label": "label", "group": "group", "tooltip": True})
        edges.append(
            {
                "data": sub_edges,
                "source": "source",
                "target": "target",
                "label": "label",
                "directed": True,
                "tooltip": True,
            }
        )

    if not edges:
        raise GraphSpecError("graph_spec must include at least one edge-bearing source")
    out["nodes"] = nodes
    out["edges"] = edges
    return out


def normalize_graph_spec(spec: Mapping[str, object], sources: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    """Validate and normalize a graph spec against its per-source DataFrames."""
    return resolve_graph_spec(parse_graph_spec(spec), sources)


def _source_rows(source: Mapping[str, object], sources: Mapping[str, pd.DataFrame]) -> list[Mapping[str, object]]:
    inline = source.get("data")
    if isinstance(inline, Sequence) and not isinstance(inline, str | bytes | bytearray):
        return [row for row in inline if isinstance(row, Mapping)]
    rid = source.get("record_id")
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


def graph_size(graph_spec: Mapping[str, object], sources: Mapping[str, pd.DataFrame]) -> GraphSize:
    """Compute final unique node and valid edge counts for a normalized graph spec."""
    node_ids: set[str] = set()
    raw_nodes = graph_spec.get("nodes")
    for raw_source in raw_nodes if isinstance(raw_nodes, list) else []:
        if not isinstance(raw_source, Mapping):
            continue
        id_field = raw_source.get("id")
        for row in _source_rows(raw_source, sources):
            node_id = _node_id(_row_value(row, id_field))
            if node_id is not None:
                node_ids.add(node_id)

    edge_count = 0
    raw_edges = graph_spec.get("edges")
    for raw_source in raw_edges if isinstance(raw_edges, list) else []:
        if not isinstance(raw_source, Mapping):
            continue
        source_field = raw_source.get("source")
        target_field = raw_source.get("target")
        for row in _source_rows(raw_source, sources):
            source_id = _node_id(_row_value(row, source_field))
            target_id = _node_id(_row_value(row, target_field))
            if source_id is None or target_id is None:
                continue
            node_ids.add(source_id)
            node_ids.add(target_id)
            edge_count += 1
    return GraphSize(nodes=len(node_ids), edges=edge_count)


def validate_graph_size(size: GraphSize) -> None:
    """Reject graph payloads that are too large for an interactive node-link view."""
    if size.edges == 0:
        raise GraphSpecError("graph has no valid edges")
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


def graph_type_label(spec: Mapping[str, object]) -> str:
    """Human-readable graph label for UI cards and tool messages."""
    return "Network graph"


class RenderGraphTool:
    """Create a node-link graph artifact from query results or inline data."""

    name: ClassVar = "render_graph"

    def __init__(self, history: QueryHistory | None = None) -> None:
        self._history = history or QueryHistory()

    async def __call__(self, *, graph_spec: str) -> str:
        """Create a graph from one or more query results.

        The spec is a JSON string containing an object with ``edges`` and
        optional ``nodes``. Each column source names the query result it reads
        from via ``record_id``. Nodes may be supplied in one result while edges
        come from another; if ``nodes`` is omitted, endpoint ids become nodes.

        Full public grammar:
        - Top level:
          ``title``: optional string.
          ``layout``: optional ``force``, ``layered``, or ``tree``.
          ``nodes``: optional list of node sources.
          ``edges``: required list of edge sources unless ``subgraph`` is used.
          ``subgraph``: optional list of Neo4j result sources containing native
          nodes, relationships, or paths.
        - Node source:
          Column mode:
          ``{"record_id":"Q1","id":"id","label":"name","group":"type"}``.
          Inline mode:
          ``{"data":[{"id":"a","name":"A"}],"id":"id","label":"name"}``.
          Optional ``tooltip`` is a field name, list of field names, or ``true``.
          Explicit tooltip lists define body fields; node titles use ``label`` or ``id``.
        - Edge source:
          Column mode:
          ``{"record_id":"Q2","source":"from_id","target":"to_id","label":"rel"}``.
          Inline mode:
          ``{"data":[{"from":"a","to":"b"}],"source":"from","target":"to"}``.
          Optional ``directed`` defaults to ``true``. Optional ``tooltip`` is a
          field name, list of field names, or ``true``. Explicit tooltip lists
          define body fields; edge titles use ``label`` when present.
        - Subgraph source:
          ``{"record_id":"Q3","caption":"title"}``. Node and relationship
          properties are copied into tooltip fields.

        Minimal examples:
        ``{"edges":[{"record_id":"Q1","source":"src","target":"dst","label":"rel"}]}``
        ``{"layout":"layered","nodes":[{"record_id":"Q1","id":"id","label":"name"}],"edges":[{"record_id":"Q2","source":"from_id","target":"to_id"}]}``
        ``{"nodes":[{"data":[{"id":"a"},{"id":"b"}],"id":"id"}],"edges":[{"data":[{"from":"a","to":"b"}],"source":"from","target":"to"}]}``

        Returns the new graph id (``GRAPH1``, ``GRAPH2``, …) to cite in the answer.

        Args:
            graph_spec: Declarative graph specification as a JSON string.
        """
        try:
            spec = json.loads(graph_spec)
        except (json.JSONDecodeError, TypeError) as e:
            return f"(error: invalid JSON — {e})"

        if not isinstance(spec, dict):
            return "(error: graph_spec must be a JSON object)"

        try:
            parsed = parse_graph_spec(spec)
        except GraphSpecError as e:
            return f"(error: {e})"

        record_ids = referenced_record_ids(parsed)
        sources: dict[str, pd.DataFrame] = {}
        for rid in record_ids:
            try:
                record = await self._history.get(rid)
            except KeyError:
                return f"(error: unknown record_id {rid!r})"
            pred = record.pred_query
            if pred.exec_result is None or pred.exec_result.df is None:
                return f"(error: query {rid} returned no data)"
            df = pred.exec_result.df
            if df.empty:
                return f"(error: query {rid} result is empty)"
            sources[rid] = df

        try:
            normalized = resolve_graph_spec(parsed, sources)
            size = graph_size(normalized, sources)
            validate_graph_size(size)
        except GraphSpecError as e:
            return f"(error: {e})"

        graph_id = self._history.add_graph(normalized)
        label = graph_type_label(normalized)
        from_text = f" from {', '.join(record_ids)}" if record_ids else ""
        return f"{label} {graph_id} created{from_text} — {size.nodes:,} nodes, {size.edges:,} edges"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
