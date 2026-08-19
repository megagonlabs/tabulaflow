"""Tests for the declarative graph tool."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

import pandas as pd
import pytest

from tabulaflow.core import ExecResult
from tabulaflow.output.specs import GraphArtifactSpec
from tabulaflow.output.store import OutputStore
from tabulaflow.output.graphs import (
    GRAPH_MAX_NODES,
    GraphEdgeSourceSpec,
    GraphLiteralValueSpec,
    GraphNodeSourceSpec,
    GraphSpec,
    graph_size,
    materialize_graph_result,
    normalize_graph_spec,
    parse_graph_spec,
    validate_graph_size,
)
from tabulaflow.agents.tools.render_graph import RenderGraphTool


async def _output_store_with(*dfs: pd.DataFrame) -> OutputStore:
    output_store = OutputStore()
    for df in dfs:
        await output_store.add_fixed_result_source("db", "sql", "SELECT 1", ExecResult(df=df))
    return output_store


def _graph_artifact(output_store: OutputStore, graph_id: str) -> GraphArtifactSpec:
    artifact = output_store.get_artifact(graph_id)
    assert isinstance(artifact, GraphArtifactSpec)
    return artifact


def _norm(spec: Mapping[str, object], **sources: pd.DataFrame) -> dict[str, Any]:
    sources = {key.replace("Q", "S", 1) if key.startswith("Q") else key: value for key, value in sources.items()}
    return normalize_graph_spec(spec, sources)


class TestNormalizeGraphSpec:
    def test_public_nested_models_construct_graph_spec(self) -> None:
        spec = GraphSpec(
            nodes=[
                GraphNodeSourceSpec(
                    data=[{"id": "a"}],
                    id="id",
                    group=GraphLiteralValueSpec(value="Person"),
                )
            ],
            edges=[GraphEdgeSourceSpec(data=[{"source": "a", "target": "a"}], source="source", target="target")],
        )

        assert spec.nodes[0].group == GraphLiteralValueSpec(value="Person")

    def test_parse_returns_public_graph_spec(self) -> None:
        parsed = parse_graph_spec(
            {
                "nodes": [{"data": [{"id": "a"}], "id": "id"}],
                "edges": [{"data": [{"source": "a", "target": "a"}], "source": "source", "target": "target"}],
            }
        )

        assert isinstance(parsed, GraphSpec)

    def test_edge_source_resolves_fields_case_insensitively(self) -> None:
        df = pd.DataFrame({"Src": ["a"], "Dst": ["b"], "Rel": ["knows"]})
        spec = {
            "nodes": [{"source_id": "S1", "id": "src"}, {"source_id": "S1", "id": "dst"}],
            "edges": [{"source_id": "S1", "source": "src", "target": "dst", "label": "rel"}],
        }
        assert _norm(spec, Q1=df) == {
            "layout": "force",
            "nodes": [{"source_id": "S1", "id": "Src"}, {"source_id": "S1", "id": "Dst"}],
            "edges": [{"source_id": "S1", "source": "Src", "target": "Dst", "label": "Rel", "directed": True}],
        }

    def test_multi_source_nodes_and_edges(self) -> None:
        nodes = pd.DataFrame({"id": ["a", "b"], "name": ["Alice", "Bob"], "team": ["x", "y"], "score": [1, 5]})
        edges = pd.DataFrame({"from_id": ["a"], "to_id": ["b"], "rel": ["knows"]})
        spec = {
            "layout": "layered",
            "nodes": [{"source_id": "S1", "id": "id", "label": "name", "group": "team"}],
            "edges": [{"source_id": "S2", "source": "from_id", "target": "to_id", "label": "rel", "directed": False}],
        }
        assert _norm(spec, Q1=nodes, Q2=edges) == {
            "layout": "layered",
            "nodes": [{"source_id": "S1", "id": "id", "label": "name", "group": "team"}],
            "edges": [{"source_id": "S2", "source": "from_id", "target": "to_id", "label": "rel", "directed": False}],
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

    def test_group_and_label_accept_constant_values(self) -> None:
        df = pd.DataFrame({"customer": ["a"], "product": ["p"]})
        spec = {
            "nodes": [
                {"source_id": "S1", "id": "customer", "group": {"value": "Customer"}},
                {"source_id": "S1", "id": "product", "group": {"value": "Product"}},
            ],
            "edges": [{"source_id": "S1", "source": "customer", "target": "product", "label": {"value": "PURCHASED"}}],
        }
        assert _norm(spec, Q1=df) == {
            "layout": "force",
            "nodes": [
                {"source_id": "S1", "id": "customer", "group": {"value": "Customer"}},
                {"source_id": "S1", "id": "product", "group": {"value": "Product"}},
            ],
            "edges": [
                {
                    "source_id": "S1",
                    "source": "customer",
                    "target": "product",
                    "label": {"value": "PURCHASED"},
                    "directed": True,
                }
            ],
        }

    def test_constant_value_must_be_non_empty(self) -> None:
        df = pd.DataFrame({"src": ["a"], "dst": ["b"]})
        with pytest.raises(ValueError, match="non-empty"):
            _norm(
                {
                    "nodes": [{"source_id": "S1", "id": "src"}, {"source_id": "S1", "id": "dst"}],
                    "edges": [{"source_id": "S1", "source": "src", "target": "dst", "label": {"value": ""}}],
                },
                Q1=df,
            )

    def test_node_only_graph_is_supported(self) -> None:
        normalized = _norm({"nodes": [{"data": [{"id": "a"}], "id": "id"}]})
        graph = materialize_graph_result(normalized, {})

        assert [node.id for node in graph.nodes] == ["a"]
        assert graph.edges == []
        validate_graph_size(graph_size(graph))

    def test_node_size_is_not_supported(self) -> None:
        spec = {
            "nodes": [{"data": [{"id": "a", "score": 1}], "id": "id", "size": "score"}],
            "edges": [{"data": [{"from": "a", "to": "b"}], "source": "from", "target": "to"}],
        }
        with pytest.raises(ValueError, match="size"):
            _norm(spec)

    def test_field_not_found_lists_columns(self) -> None:
        df = pd.DataFrame({"src": ["a"], "dst": ["b"]})
        with pytest.raises(ValueError, match="Available columns"):
            _norm(
                {
                    "nodes": [{"source_id": "S1", "id": "src"}],
                    "edges": [{"source_id": "S1", "source": "src", "target": "missing"}],
                },
                Q1=df,
            )

    def test_edges_without_node_sources_rejected(self) -> None:
        df = pd.DataFrame({"src": ["a"], "dst": ["b"]})
        with pytest.raises(ValueError, match="nodes"):
            _norm({"edges": [{"source_id": "S1", "source": "src", "target": "dst"}]}, Q1=df)

    def test_unmatched_edge_endpoints_rejected(self) -> None:
        df = pd.DataFrame({"src": ["a", "b"], "dst": ["b", "c"]})
        normalized = _norm(
            {
                "nodes": [{"source_id": "S1", "id": "src"}],
                "edges": [{"source_id": "S1", "source": "src", "target": "dst"}],
            },
            Q1=df,
        )
        with pytest.raises(ValueError, match="match no node source id.*'c'"):
            materialize_graph_result(normalized, {"S1": df})

    def test_graph_size_counts_groups_first_source_wins(self) -> None:
        nodes1 = pd.DataFrame({"id": ["a"], "kind": ["x"]})
        nodes2 = pd.DataFrame({"id": ["a", "b"]})
        edges = pd.DataFrame({"src": ["a"], "dst": ["c"]})
        normalized = _norm(
            {
                "nodes": [
                    {"source_id": "S1", "id": "id", "group": "kind"},
                    {"source_id": "S2", "id": "id", "group": {"value": "y"}},
                    {"source_id": "S3", "id": "dst"},
                ],
                "edges": [{"source_id": "S3", "source": "src", "target": "dst"}],
            },
            Q1=nodes1,
            Q2=nodes2,
            Q3=edges,
        )
        graph = materialize_graph_result(normalized, {"S1": nodes1, "S2": nodes2, "S3": edges})
        size = graph_size(graph)
        assert size.nodes == 3
        assert size.edges == 1
        assert size.groups == 2  # a keeps 'x' from its first source; b gets the constant 'y'
        assert size.ungrouped_nodes == 1  # c is declared without a group

    def test_subgraph_mode_is_not_supported(self) -> None:
        with pytest.raises(ValueError, match="subgraph"):
            _norm({"subgraph": [{"source_id": "S1"}]})

    def test_materialized_graph_properties_use_json_null_for_non_finite_values(self) -> None:
        df = pd.DataFrame(
            {
                "src": ["director"],
                "dst": ["movie"],
                "src_rating": [math.nan],
                "edge_rating": [math.inf],
            }
        )
        spec = _norm(
            {
                "nodes": [
                    {"source_id": "S1", "id": "src", "tooltip": "src_rating"},
                    {"source_id": "S1", "id": "dst"},
                ],
                "edges": [{"source_id": "S1", "source": "src", "target": "dst", "tooltip": "edge_rating"}],
            },
            Q1=df,
        )

        graph = materialize_graph_result(spec, {"S1": df})

        assert graph.nodes[0].properties["src_rating"] is None
        assert graph.edges[0].properties["edge_rating"] is None


class TestRenderGraphTool:
    async def test_node_only_graph_created(self) -> None:
        output_store = await _output_store_with(pd.DataFrame({"id": ["a", "b"], "kind": ["Person", "Company"]}))
        spec = {"nodes": [{"source_id": "S1", "id": "id", "group": "kind"}]}

        msg = await RenderGraphTool(output_store=output_store)(graph_spec=json.dumps(spec))

        assert "Network graph GRAPH1 created from S1" in msg
        assert "2 nodes in 2 types, 0 edges" in msg

    async def test_graph_created(self) -> None:
        output_store = await _output_store_with(pd.DataFrame({"src": ["a", "b"], "dst": ["b", "c"], "rel": ["x", "y"]}))
        spec = {
            "title": "Lineage",
            "nodes": [{"source_id": "S1", "id": "src"}, {"source_id": "S1", "id": "dst"}],
            "edges": [{"source_id": "S1", "source": "src", "target": "dst", "label": "rel"}],
        }
        msg = await RenderGraphTool(output_store=output_store)(graph_spec=json.dumps(spec))
        assert "Network graph GRAPH1 created from S1" in msg
        assert "3 nodes, 2 edges (all nodes one color; set group on node sources to color by type)" in msg
        graph = materialize_graph_result(
            _graph_artifact(output_store, "GRAPH1").spec, {"S1": (await output_store.get_payload("R1")).df}
        )
        assert graph.edges[0].source == "a"
        assert graph.edges[0].target == "b"

    async def test_graph_created_reports_node_types(self) -> None:
        output_store = await _output_store_with(
            pd.DataFrame({"account": ["a", "b"], "merchant": ["m1", "m2"], "rel": ["paid", "paid"]})
        )
        spec = {
            "nodes": [
                {"source_id": "S1", "id": "account", "group": {"value": "Account"}},
                {"source_id": "S1", "id": "merchant", "group": {"value": "Merchant"}},
            ],
            "edges": [{"source_id": "S1", "source": "account", "target": "merchant", "label": "rel"}],
        }
        msg = await RenderGraphTool(output_store=output_store)(graph_spec=json.dumps(spec))
        assert "4 nodes in 2 types, 2 edges" in msg
        assert "one color" not in msg

    async def test_final_node_cap_uses_unique_node_ids(self) -> None:
        df = pd.DataFrame(
            {
                "src": [f"s{i}" for i in range(GRAPH_MAX_NODES + 1)],
                "dst": [f"d{i}" for i in range(GRAPH_MAX_NODES + 1)],
            }
        )
        output_store = await _output_store_with(df)
        spec = {
            "nodes": [{"source_id": "S1", "id": "src"}, {"source_id": "S1", "id": "dst"}],
            "edges": [{"source_id": "S1", "source": "src", "target": "dst"}],
        }
        msg = await RenderGraphTool(output_store=output_store)(graph_spec=json.dumps(spec))
        assert "too large" in msg
        assert "nodes" in msg
        assert output_store._artifacts == {}
