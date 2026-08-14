"""Model-facing tool for creating graph output artifacts."""

import json
from typing import ClassVar
import pandas as pd
from pydantic_ai import Tool

from tabulaflow.output.graphs import (
    GraphSpecError,
    graph_type_label,
    graph_result_size,
    materialize_graph_result,
    parse_graph_spec,
    referenced_source_ids,
    resolve_graph_spec,
    validate_graph_size,
)
from tabulaflow.output.specs import FixedResultSource
from tabulaflow.output.store import OutputStore


class RenderGraphTool:
    """Create a node-link graph artifact from query results or inline data."""

    name: ClassVar = "render_graph"

    def __init__(self, output_store: OutputStore | None = None) -> None:
        self._output_store = output_store or OutputStore()

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
          ``{"source_id":"S1","id":"id","label":"name","group":"type"}``.
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
          ``{"source_id":"S2","source":"from_id","target":"to_id","label":"rel"}``.
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
        ``{"nodes":[{"source_id":"S1","id":"src"},{"source_id":"S1","id":"dst"}],"edges":[{"source_id":"S1","source":"src","target":"dst","label":"rel"}]}``
        ``{"layout":"layered","nodes":[{"source_id":"S1","id":"id","label":"name"}],"edges":[{"source_id":"S2","source":"from_id","target":"to_id"}]}``
        ``{"nodes":[{"data":[{"id":"a"},{"id":"b"}],"id":"id"}],"edges":[{"data":[{"from":"a","to":"b"}],"source":"from","target":"to"}]}``
        ``{"nodes":[{"source_id":"S1","id":"customer","group":{"value":"Customer"}},{"source_id":"S1","id":"product","group":{"value":"Product"}}],"edges":[{"source_id":"S1","source":"customer","target":"product","label":{"value":"PURCHASED"}}]}``

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
                source = self._output_store.get_source(rid)
                if not isinstance(source, FixedResultSource):
                    return f"(error: source_id {rid!r} is not a single-result source)"
                result_id = source.result_id
            except KeyError:
                return f"(error: unknown source_id {rid!r})"
            except ValueError as e:
                return f"(error: {e})"
            try:
                df = (await self._output_store.get_payload(result_id)).df
            except ValueError as e:
                return f"(error: {e})"
            if df is None:
                return f"(error: query {rid} returned no data)"
            if df.empty:
                return f"(error: query {rid} result is empty)"
            sources[rid] = df

        try:
            normalized = resolve_graph_spec(parsed, sources)
            graph = materialize_graph_result(normalized, sources)
            size = graph_result_size(graph)
            validate_graph_size(size)
        except GraphSpecError as e:
            return f"(error: {e})"

        artifact = self._output_store.add_graph_artifact(source_ids, normalized)
        graph_id = artifact.id
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
