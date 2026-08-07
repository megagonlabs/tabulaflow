"""Tool that stores a declarative node-link graph artifact."""

from __future__ import annotations

import copy
import json
import numbers
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from pydantic_ai import Tool

from tabulaflow.core.types import GraphView
from tabulaflow.core.utils import json_ready
from tabulaflow.toolhub.query_history import QueryHistory
from tabulaflow.toolhub.render_map import resolve_column

GRAPH_MAX_NODES = 300
GRAPH_MAX_EDGES = 700


class GraphSpecError(ValueError):
    """Raised when a graph spec cannot be applied to a result."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _ValueRef(_StrictModel):
    value: str


class _SourceModel(_StrictModel):
    source_id: str | None = None
    data: list[dict[str, Any]] | None = None

    @model_validator(mode="after")
    def _validate_source_mode(self) -> _SourceModel:
        has_record = self.source_id is not None
        has_data = self.data is not None
        if has_record == has_data:
            raise ValueError("graph sources must set exactly one of source_id or data")
        if self.data is not None and not self.data:
            raise ValueError("inline graph data must be a non-empty list")
        return self


class _NodeSource(_SourceModel):
    id: str
    label: str | None = None
    group: str | _ValueRef | None = None
    tooltip: str | list[str] | Literal[True] | None = None


class _EdgeSource(_SourceModel):
    source: str
    target: str
    label: str | _ValueRef | None = None
    directed: bool = True
    tooltip: str | list[str] | Literal[True] | None = None


class _GraphSpec(_StrictModel):
    title: str | None = None
    layout: Literal["force", "layered", "tree"] = "force"
    nodes: list[_NodeSource] = []
    edges: list[_EdgeSource] = []

    @model_validator(mode="after")
    def _require_sources(self) -> _GraphSpec:
        if not self.edges:
            raise ValueError("graph_spec must include at least one edge-bearing source")
        if not self.nodes:
            raise ValueError("edges require node sources: declare one per endpoint column with id, label, and group")
        return self


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


def _field_or_value(
    resolve_field: Callable[..., str], value: str | _ValueRef | None, *, path: str
) -> str | dict[str, str] | None:
    if isinstance(value, _ValueRef):
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


def parse_graph_spec(spec: Mapping[str, object]) -> _GraphSpec:
    """Validate a raw graph spec into a typed model, raising ``GraphSpecError``."""
    try:
        return _GraphSpec.model_validate(spec)
    except ValidationError as e:
        raise GraphSpecError(_validation_message(e)) from None


def referenced_source_ids(parsed: _GraphSpec) -> list[str]:
    """Return the distinct query-history source ids referenced by a parsed spec."""
    ids: list[str] = []
    all_sources: list[_NodeSource | _EdgeSource] = [
        *parsed.nodes,
        *parsed.edges,
    ]
    for source in all_sources:
        rid = source.source_id
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
        df = sources.get(node_source.source_id) if node_source.source_id is not None else None
        if node_source.source_id is not None and df is None:
            raise GraphSpecError(f"nodes[{index}] references unknown source_id {node_source.source_id!r}")
        nodes.append(_normalize_node_source(df, node_source, index))
    for index, edge_source in enumerate(parsed.edges):
        df = sources.get(edge_source.source_id) if edge_source.source_id is not None else None
        if edge_source.source_id is not None and df is None:
            raise GraphSpecError(f"edges[{index}] references unknown source_id {edge_source.source_id!r}")
        edges.append(_normalize_edge_source(df, edge_source, index))

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


def materialize_graph_view(graph_spec: Mapping[str, object], sources: Mapping[str, pd.DataFrame]) -> GraphView:
    """Materialize a normalized graph spec into the typed graph-view data contract."""
    nodes_by_id: dict[str, dict[str, object]] = {}
    raw_nodes = graph_spec.get("nodes")
    for raw_source in raw_nodes if isinstance(raw_nodes, list) else []:
        if not isinstance(raw_source, Mapping):
            continue
        id_field = raw_source.get("id")
        label_field = raw_source.get("label")
        group_field = raw_source.get("group")
        constant_group = _constant_value(group_field)
        for row in _source_rows(raw_source, sources):
            node_id = _node_id(_row_value(row, id_field))
            if node_id is None or node_id in nodes_by_id:
                continue
            label = _row_value(row, label_field) if isinstance(label_field, str) else None
            group = constant_group if constant_group is not None else _row_value(row, group_field)
            properties = _properties(row, raw_source.get("tooltip"))
            node: dict[str, object] = {"id": node_id}
            if label is not None:
                node["label"] = str(label)
            if group is not None:
                node["group"] = str(group)
            if properties:
                node["properties"] = properties
            nodes_by_id[node_id] = node

    edges: list[dict[str, object]] = []
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
            edge: dict[str, object] = {"source": source_id, "target": target_id, "directed": directed}
            if label is not None:
                edge["label"] = str(label)
            if properties:
                edge["properties"] = properties
            edges.append(edge)

    if unmatched:
        sample = ", ".join(repr(node_id) for node_id in sorted(unmatched)[:5])
        raise GraphSpecError(
            f"{len(unmatched)} edge endpoint id(s) match no node source id (e.g. {sample}); "
            "declare a node source covering every endpoint column"
        )

    return GraphView(
        nodes=sorted(nodes_by_id.values(), key=lambda node: str(node["id"])),
        edges=edges,
    )


def graph_view_size(graph: GraphView) -> GraphSize:
    groups = {node.group for node in graph.nodes if node.group is not None}
    ungrouped = sum(1 for node in graph.nodes if node.group is None)
    return GraphSize(nodes=len(graph.nodes), edges=len(graph.edges), groups=len(groups), ungrouped_nodes=ungrouped)


def graph_size(graph_spec: Mapping[str, object], sources: Mapping[str, pd.DataFrame]) -> GraphSize:
    """Compute unique node, valid edge, and node-type counts for a normalized graph spec.

    Mirrors the renderer's first-source-wins node dedup: the source that first
    introduces a node id also fixes whether it is grouped. Raises
    ``GraphSpecError`` when an edge endpoint matches no declared node id.
    """
    return graph_view_size(materialize_graph_view(graph_spec, sources))


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
        """Create a graph from one or more query results. Use this when the
        source is not Neo4j or the graph needs to be customized.

        The spec is a JSON string containing an object with ``nodes`` and
        ``edges``. Each column source names the query result it reads from via
        ``source_id``. Nodes may be supplied in one result while edges come
        from another; every edge endpoint id must match a declared node id.

        Full public grammar:
        - Top level:
          ``title``: optional string.
          ``layout``: optional ``force``, ``layered``, or ``tree``.
          ``nodes``: required list of node sources.
          ``edges``: required list of edge sources.
        - Node source:
          Column mode:
          ``{"source_id":"Q1","id":"id","label":"name","group":"type"}``.
          Inline mode:
          ``{"data":[{"id":"a","name":"A"}],"id":"id","label":"name"}``.
          Node ``id`` values are global across all sources: equal ids are
          the same node (the first source wins) and every edge endpoint
          must match one, so id spaces that overlap across types must be
          disambiguated (e.g. prefixed) in the query.
          ``group`` is the node's categorical type (not an identifier);
          nodes are colored one color per distinct group value. It is a
          column name, or ``{"value":"Customer"}`` when all nodes from
          the source share one type; omit it for untyped nodes.
          Optional ``tooltip`` is a field name, list of field names, or
          ``true`` (all row fields). Explicit tooltip lists define body
          fields; node titles use ``label`` or ``id``.
        - Edge source:
          Column mode:
          ``{"source_id":"Q2","source":"from_id","target":"to_id","label":"rel"}``.
          Inline mode:
          ``{"data":[{"from":"a","to":"b"}],"source":"from","target":"to"}``.
          ``label`` is drawn along the edge (typically the relationship
          type): a column name, or ``{"value":"PURCHASED"}`` when all
          edges from the source share one type.
          Optional ``directed`` defaults to ``true``. Optional ``tooltip`` is a
          field name, list of field names, or ``true`` (all row fields).
          Explicit tooltip lists define body fields; edge titles use ``label``
          when present.
        Minimal examples:
        ``{"nodes":[{"source_id":"Q1","id":"src"},{"source_id":"Q1","id":"dst"}],"edges":[{"source_id":"Q1","source":"src","target":"dst","label":"rel"}]}``
        ``{"layout":"layered","nodes":[{"source_id":"Q1","id":"id","label":"name"}],"edges":[{"source_id":"Q2","source":"from_id","target":"to_id"}]}``
        ``{"nodes":[{"data":[{"id":"a"},{"id":"b"}],"id":"id"}],"edges":[{"data":[{"from":"a","to":"b"}],"source":"from","target":"to"}]}``
        ``{"nodes":[{"source_id":"Q1","id":"customer","group":{"value":"Customer"}},{"source_id":"Q1","id":"product","group":{"value":"Product"}}],"edges":[{"source_id":"Q1","source":"customer","target":"product","label":{"value":"PURCHASED"}}]}``

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

        source_ids = referenced_source_ids(parsed)
        sources: dict[str, pd.DataFrame] = {}
        for rid in source_ids:
            try:
                await self._history.get(rid)
            except KeyError:
                return f"(error: unknown source_id {rid!r})"
            try:
                df = await self._history.get_dataframe(rid)
            except ValueError as e:
                return f"(error: {e})"
            if df.empty:
                return f"(error: query {rid} result is empty)"
            sources[rid] = df

        try:
            normalized = resolve_graph_spec(parsed, sources)
            graph = materialize_graph_view(normalized, sources)
            size = graph_view_size(graph)
            validate_graph_size(size)
        except GraphSpecError as e:
            return f"(error: {e})"

        graph_id = self._history.add_graph(normalized)
        label = graph_type_label(normalized)
        from_text = f" from {', '.join(source_ids)}" if source_ids else ""
        if size.groups == 0:
            counts = (
                f"{size.nodes:,} nodes, {size.edges:,} edges "
                "(all nodes one color; set group on node sources to color by type)"
            )
        else:
            types_text = f"{size.groups:,} type" + ("" if size.groups == 1 else "s")
            untyped_text = f" ({size.ungrouped_nodes:,} untyped)" if size.ungrouped_nodes else ""
            counts = f"{size.nodes:,} nodes in {types_text}{untyped_text}, {size.edges:,} edges"
        return f"{label} {graph_id} created{from_text} — {counts}"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
