"""Tests for the declarative graph tool."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub.query_history import QueryHistory
from tabulaflow.toolhub.render_graph import GRAPH_MAX_NODES, RenderGraphTool, graph_size, normalize_graph_spec


async def _history_with(*dfs: pd.DataFrame) -> QueryHistory:
    history = QueryHistory()
    for df in dfs:
        await history.add("db", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=df)))
    return history


def _norm(spec: dict, **sources: pd.DataFrame) -> dict:
    return normalize_graph_spec(spec, sources)


class TestNormalizeGraphSpec:
    def test_edge_source_resolves_fields_case_insensitively(self) -> None:
        df = pd.DataFrame({"Src": ["a"], "Dst": ["b"], "Rel": ["knows"]})
        spec = {"edges": [{"record_id": "Q1", "source": "src", "target": "dst", "label": "rel"}]}
        assert _norm(spec, Q1=df) == {
            "layout": "force",
            "nodes": [],
            "edges": [{"record_id": "Q1", "source": "Src", "target": "Dst", "label": "Rel", "directed": True}],
        }

    def test_multi_source_nodes_and_edges(self) -> None:
        nodes = pd.DataFrame({"id": ["a", "b"], "name": ["Alice", "Bob"], "team": ["x", "y"], "score": [1, 5]})
        edges = pd.DataFrame({"from_id": ["a"], "to_id": ["b"], "rel": ["knows"]})
        spec = {
            "layout": "layered",
            "nodes": [{"record_id": "Q1", "id": "id", "label": "name", "group": "team", "size": "score"}],
            "edges": [{"record_id": "Q2", "source": "from_id", "target": "to_id", "label": "rel", "directed": False}],
        }
        assert _norm(spec, Q1=nodes, Q2=edges) == {
            "layout": "layered",
            "nodes": [{"record_id": "Q1", "id": "id", "label": "name", "group": "team", "size": "score"}],
            "edges": [{"record_id": "Q2", "source": "from_id", "target": "to_id", "label": "rel", "directed": False}],
        }

    def test_inline_sources_are_supported(self) -> None:
        spec = {
            "nodes": [{"data": [{"id": "a", "name": "Alice"}], "id": "id", "label": "name"}],
            "edges": [{"data": [{"from": "a", "to": "b"}], "source": "from", "target": "to"}],
        }
        assert _norm(spec) == {
            "layout": "force",
            "nodes": [{"data": [{"id": "a", "name": "Alice"}], "id": "id", "label": "name"}],
            "edges": [{"data": [{"from": "a", "to": "b"}], "source": "from", "target": "to", "directed": True}],
        }

    def test_requires_edge_source(self) -> None:
        with pytest.raises(ValueError, match="edge-bearing"):
            _norm({"nodes": [{"data": [{"id": "a"}], "id": "id"}]})

    def test_field_not_found_lists_columns(self) -> None:
        df = pd.DataFrame({"src": ["a"], "dst": ["b"]})
        with pytest.raises(ValueError, match="Available columns"):
            _norm({"edges": [{"record_id": "Q1", "source": "src", "target": "missing"}]}, Q1=df)

    def test_graph_size_counts_implicit_endpoint_nodes(self) -> None:
        df = pd.DataFrame({"src": ["a", "b"], "dst": ["b", "c"]})
        normalized = _norm({"edges": [{"record_id": "Q1", "source": "src", "target": "dst"}]}, Q1=df)
        assert graph_size(normalized, {"Q1": df}).nodes == 3
        assert graph_size(normalized, {"Q1": df}).edges == 2


class TestRenderGraphTool:
    async def test_graph_created(self) -> None:
        history = await _history_with(pd.DataFrame({"src": ["a", "b"], "dst": ["b", "c"], "rel": ["x", "y"]}))
        spec = {
            "title": "Lineage",
            "edges": [{"record_id": "Q1", "source": "src", "target": "dst", "label": "rel"}],
        }
        msg = await RenderGraphTool(history=history)(graph_spec=json.dumps(spec))
        assert "Lineage GRAPH1 created from Q1" in msg
        assert "3 nodes, 2 edges" in msg
        assert history.get_graph("GRAPH1").graph_spec["edges"][0]["source"] == "src"

    async def test_final_node_cap_uses_unique_endpoint_nodes(self) -> None:
        df = pd.DataFrame(
            {
                "src": [f"s{i}" for i in range(GRAPH_MAX_NODES + 1)],
                "dst": [f"d{i}" for i in range(GRAPH_MAX_NODES + 1)],
            }
        )
        history = await _history_with(df)
        spec = {"edges": [{"record_id": "Q1", "source": "src", "target": "dst"}]}
        msg = await RenderGraphTool(history=history)(graph_spec=json.dumps(spec))
        assert "too large" in msg
        assert "nodes" in msg
        assert history._graphs == {}
