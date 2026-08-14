from __future__ import annotations

from datetime import date
import math

import pandas as pd
from neo4j.graph import Graph, Node, Path, Relationship

from tabulaflow.data.neo4j import _extract_neo4j_graph_result


def _neo4j_objects() -> tuple[Node, Node, Relationship, Path]:
    graph = Graph()
    alice = Node(
        graph,
        "alice-id",
        1,
        ["Person"],
        {
            "name": "Alice",
            "age": 36,
            "tags": ["lead", "founder"],
            "profile": {"city": "Oakland", "active": True},
            "born": date(1988, 3, 4),
        },
    )
    matrix = Node(graph, "matrix-id", 2, ["Movie"], {"title": "The Matrix", "released": 1999})
    rel_cls = graph.relationship_type("ACTED_IN")
    acted_in = rel_cls(
        graph,
        "acted-in-id",
        3,
        {"role": "Trinity", "scenes": ["lobby", "rooftop"], "metadata": {"billing": 2}},
    )
    acted_in._start_node = alice
    acted_in._end_node = matrix
    return alice, matrix, acted_in, Path(alice, acted_in)


def test_extracts_dynamic_relationship_subclasses() -> None:
    alice, matrix, acted_in, _ = _neo4j_objects()
    result = _extract_neo4j_graph_result(pd.DataFrame({"nodes": [[alice, matrix]], "relationships": [[acted_in]]}))

    assert result is not None
    assert [node.model_dump(exclude_none=True) for node in result.nodes] == [
        {
            "id": "alice-id",
            "label": "Alice",
            "group": "Person",
            "properties": {
                "name": "Alice",
                "age": 36,
                "tags": ["lead", "founder"],
                "profile": {"city": "Oakland", "active": True},
                "born": "1988-03-04",
            },
        },
        {
            "id": "matrix-id",
            "label": "The Matrix",
            "group": "Movie",
            "properties": {"title": "The Matrix", "released": 1999},
        },
    ]
    assert [edge.model_dump(exclude_none=True) for edge in result.edges] == [
        {
            "id": "acted-in-id",
            "source": "alice-id",
            "target": "matrix-id",
            "label": "ACTED_IN",
            "directed": True,
            "properties": {"role": "Trinity", "scenes": ["lobby", "rooftop"], "metadata": {"billing": 2}},
        }
    ]


def test_recursively_extracts_nested_paths_and_relationships() -> None:
    _, _, acted_in, path = _neo4j_objects()
    result = _extract_neo4j_graph_result(pd.DataFrame({"payload": [{"items": [{"path": path}, [acted_in]]}]}))

    assert result is not None
    assert len(result.nodes) == 2
    assert [edge.model_dump(exclude_none=True) for edge in result.edges] == [
        {
            "id": "acted-in-id",
            "source": "alice-id",
            "target": "matrix-id",
            "label": "ACTED_IN",
            "directed": True,
            "properties": {"role": "Trinity", "scenes": ["lobby", "rooftop"], "metadata": {"billing": 2}},
        }
    ]


def test_extracts_node_only_results() -> None:
    alice, _, _, _ = _neo4j_objects()
    result = _extract_neo4j_graph_result(pd.DataFrame({"node": [alice]}))

    assert result is not None
    assert result.nodes[0].id == "alice-id"
    assert result.edges == []


def test_extracts_non_finite_graph_properties_as_null() -> None:
    graph = Graph()
    movie = Node(graph, "movie-id", 1, ["Movie"], {"title": "Movie", "imdb_rating": math.nan})
    actor = Node(graph, "actor-id", 2, ["Person"], {"name": "Actor", "score": math.inf})
    rel_cls = graph.relationship_type("ACTED_IN")
    rel = rel_cls(graph, "rel-id", 3, {"confidence": math.nan})
    rel._start_node = actor
    rel._end_node = movie

    result = _extract_neo4j_graph_result(pd.DataFrame({"node": [movie], "relationship": [rel]}))

    assert result is not None
    by_id = {node.id: node for node in result.nodes}
    assert by_id["movie-id"].properties["imdb_rating"] is None
    assert by_id["actor-id"].properties["score"] is None
    assert result.edges[0].properties["confidence"] is None


def test_returns_none_without_graph_objects() -> None:
    assert _extract_neo4j_graph_result(pd.DataFrame({"x": [1]})) is None
