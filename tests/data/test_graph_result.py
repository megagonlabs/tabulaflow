from __future__ import annotations

from datetime import date
import math

from neo4j.graph import Graph, Node, Relationship
from neo4j.time import Date, DateTime, Duration, Time

from tabulaflow.core import GraphResult
from tabulaflow.data.neo4j import _convert_neo4j_graph_result


def _convert(graph: Graph, *, max_nodes: int | None = 300, max_edges: int | None = 700) -> GraphResult | None:
    return _convert_neo4j_graph_result(graph, max_nodes=max_nodes, max_edges=max_edges)


def _neo4j_graph() -> tuple[Graph, Node, Node, Relationship]:
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
    graph._nodes.update({alice.element_id: alice, matrix.element_id: matrix})
    graph._relationships[acted_in.element_id] = acted_in
    return graph, alice, matrix, acted_in


def test_extracts_dynamic_relationship_subclasses() -> None:
    graph, _, _, _ = _neo4j_graph()
    result = _convert(graph)

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


def test_extracts_node_only_results() -> None:
    graph, alice, _, _ = _neo4j_graph()
    graph._nodes.pop("matrix-id")
    graph._relationships.clear()
    result = _convert(graph)

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
    graph._nodes.update({movie.element_id: movie, actor.element_id: actor})
    graph._relationships[rel.element_id] = rel

    result = _convert(graph)

    assert result is not None
    by_id = {node.id: node for node in result.nodes}
    assert by_id["movie-id"].properties["imdb_rating"] is None
    assert by_id["actor-id"].properties["score"] is None
    assert result.edges[0].properties["confidence"] is None


def test_extracts_temporal_graph_properties_as_iso_text() -> None:
    graph = Graph()
    event = Node(
        graph,
        "event-id",
        1,
        ["Event"],
        {
            "day": Date(2024, 1, 2),
            "created_at": DateTime(2024, 1, 2, 3, 4, 5),
            "time": Time(3, 4, 5),
            "duration": Duration(months=1, days=2, seconds=3),
        },
    )
    graph._nodes[event.element_id] = event

    result = _convert(graph)

    assert result is not None
    assert result.nodes[0].properties == {
        "day": "2024-01-02",
        "created_at": "2024-01-02T03:04:05.000000000",
        "time": "03:04:05.000000000",
        "duration": "P1M2DT3S",
    }


def test_returns_none_without_graph_objects() -> None:
    assert _convert(Graph()) is None


def test_returns_none_when_node_limit_is_exceeded() -> None:
    graph = Graph()
    nodes = [Node(graph, f"node-{index}", index, ["Node"], {}) for index in range(3)]
    graph._nodes.update({node.element_id: node for node in nodes})

    assert _convert(graph, max_nodes=3) is not None
    assert _convert(graph, max_nodes=2) is None


def test_returns_none_when_relationship_would_exceed_edge_limit() -> None:
    graph, alice, matrix, _ = _neo4j_graph()
    rel_cls = graph.relationship_type("LIKES")
    likes = rel_cls(graph, "likes-id", 4, {})
    likes._start_node = alice
    likes._end_node = matrix
    graph._relationships[likes.element_id] = likes

    assert _convert(graph, max_edges=1) is None
