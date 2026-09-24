import math
import struct
from base64 import b64encode
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from tabulaflow.app.pane.cards import (
    GraphCardInput,
    MapCardInput,
    ResultCardInput,
    render_graph_data,
    render_map_data,
    render_result_data,
)
from tabulaflow.app.pane.contract import PaneCard
from tabulaflow.core import GraphResult
from tabulaflow.output.graphs import materialize_graph_result, normalize_graph_spec
from tabulaflow.output.maps import normalize_map_spec


def _result_input(
    *,
    result_id: str,
    label: str,
    query: str | None,
    df: pd.DataFrame | None,
    chart_spec: dict[str, object] | None = None,
    graph: GraphResult | None = None,
    query_lexer: str = "sql",
) -> ResultCardInput:
    return ResultCardInput(
        label=label,
        query=query,
        df=df,
        chart_spec=chart_spec,
        graph=graph,
        query_lexer=query_lexer,
    )


def _map_card(
    *,
    map_id: str,
    label: str,
    title: str,
    layers: list[dict[str, object]],
    sources: dict[str, pd.DataFrame],
    pane_dir: Path,
) -> PaneCard:
    """Build a map card via the real spec → normalize → render pipeline."""
    normalized = normalize_map_spec({"title": title, "layers": layers}, sources)
    card = render_map_data(MapCardInput(label=label, spec=normalized, sources=sources), pane_dir)
    assert card is not None
    return card


def _graph_card(
    *,
    graph_id: str,
    label: str,
    graph_spec: dict[str, object],
    sources: dict[str, pd.DataFrame],
    pane_dir: Path,
) -> PaneCard:
    """Build a graph card via the real spec → normalize → render pipeline."""
    normalized = normalize_graph_spec(graph_spec, sources)
    graph = materialize_graph_result(normalized, sources)
    card = render_graph_data(
        GraphCardInput(label=label, graph=graph, layout=str(normalized.get("layout", "force"))), pane_dir
    )
    assert card is not None
    return card


def _render_result_inputs(result_inputs: Sequence[ResultCardInput], pane_dir: Path) -> list[PaneCard]:
    cards: list[PaneCard] = []
    for result_input in result_inputs:
        card = render_result_data(result_input, pane_dir)
        if card is not None:
            cards.append(card)
    return cards


def _map_showcase_card(pane_dir: Path) -> PaneCard:
    df = pd.DataFrame(
        [
            {
                "name": "Red pin marker",
                "kind": "points layer",
                "url": "https://www.sanjose.org/",
                "lat": 37.3336,
                "lng": -121.8906,
                "geom": None,
            },
            {
                "name": "GeoJSON point",
                "kind": "Point",
                "url": "https://geojson.org/",
                "lat": None,
                "lng": None,
                "geom": {"type": "Point", "coordinates": [-121.8815, 37.3394]},
            },
            {
                "name": "GeoJSON multipoint",
                "kind": "MultiPoint",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.3",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "MultiPoint",
                    "coordinates": [[-121.906, 37.329], [-121.900, 37.337], [-121.894, 37.331]],
                },
            },
            {
                "name": "GeoJSON line",
                "kind": "LineString",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "LineString",
                    "coordinates": [[-121.915, 37.345], [-121.904, 37.350], [-121.890, 37.346]],
                },
            },
            {
                "name": "GeoJSON multiline",
                "kind": "MultiLineString",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.5",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [[-121.925, 37.322], [-121.914, 37.327], [-121.905, 37.324]],
                        [[-121.892, 37.321], [-121.882, 37.328], [-121.873, 37.323]],
                    ],
                },
            },
            {
                "name": "GeoJSON polygon",
                "kind": "Polygon",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-121.923, 37.354],
                            [-121.908, 37.354],
                            [-121.908, 37.364],
                            [-121.923, 37.364],
                            [-121.923, 37.354],
                        ]
                    ],
                },
            },
            {
                "name": "GeoJSON multipolygon",
                "kind": "MultiPolygon",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [-121.888, 37.352],
                                [-121.879, 37.352],
                                [-121.879, 37.359],
                                [-121.888, 37.359],
                                [-121.888, 37.352],
                            ]
                        ],
                        [
                            [
                                [-121.874, 37.350],
                                [-121.866, 37.350],
                                [-121.866, 37.357],
                                [-121.874, 37.357],
                                [-121.874, 37.350],
                            ]
                        ],
                    ],
                },
            },
            {
                "name": "GeoJSON geometry collection",
                "kind": "GeometryCollection",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.8",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "GeometryCollection",
                    "geometries": [
                        {"type": "Point", "coordinates": [-121.864, 37.337]},
                        {
                            "type": "LineString",
                            "coordinates": [[-121.869, 37.333], [-121.857, 37.342]],
                        },
                    ],
                },
            },
        ]
    )
    return _map_card(
        map_id="MAPDEBUG_SHOWCASE",
        label="geometry_showcase",
        title="Geometry showcase (single source)",
        sources={"QDEBUG_MAP": df},
        pane_dir=pane_dir,
        layers=[
            {
                "type": "points",
                "source_id": "QDEBUG_MAP",
                "lat": "lat",
                "lng": "lng",
                "label": "name",
                "tooltip": ["kind", "url"],
                "color": {"field": "kind"},
            },
            {
                "type": "geojson",
                "source_id": "QDEBUG_MAP",
                "geojson": "geom",
                "label": "name",
                "tooltip": ["kind", "url"],
                "color": {"field": "kind"},
            },
            {
                "type": "points",
                "points": [
                    {
                        "lat": 37.350,
                        "lng": -121.890,
                        "label": "Inline destination",
                        "kind": "inline point",
                        "url": "https://www.sanjose.org/",
                    }
                ],
                "label": "label",
                "tooltip": ["kind", "url"],
                "color": {"field": "kind"},
            },
        ],
    )


def _map_overlay_card(pane_dir: Path) -> PaneCard:
    """Multi-card overlay: neighborhood boundaries (Q1) + store points (Q2)."""
    areas = pd.DataFrame(
        [
            {
                "area": "Downtown",
                "tier": "core",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-121.895, 37.330],
                            [-121.878, 37.330],
                            [-121.878, 37.342],
                            [-121.895, 37.342],
                            [-121.895, 37.330],
                        ]
                    ],
                },
            },
            {
                "area": "North San Jose",
                "tier": "growth",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-121.945, 37.370],
                            [-121.915, 37.370],
                            [-121.915, 37.395],
                            [-121.945, 37.395],
                            [-121.945, 37.370],
                        ]
                    ],
                },
            },
        ]
    )
    stores = pd.DataFrame(
        [
            {"store": "Market St", "status": "open", "lat": 37.335, "lng": -121.888},
            {"store": "First St", "status": "open", "lat": 37.337, "lng": -121.886},
            {"store": "Almaden", "status": "closed", "lat": 37.332, "lng": -121.890},
            {"store": "Rio Robles", "status": "open", "lat": 37.382, "lng": -121.930},
            {"store": "Zanker", "status": "closed", "lat": 37.388, "lng": -121.925},
        ]
    )
    return _map_card(
        map_id="MAPDEBUG_OVERLAY",
        label="stores_by_area",
        title="Stores by service area (two query results)",
        sources={"Q_AREAS": areas, "Q_STORES": stores},
        pane_dir=pane_dir,
        layers=[
            {
                "type": "geojson",
                "source_id": "Q_AREAS",
                "geojson": "boundary",
                "label": "area",
                "tooltip": ["tier"],
                "color": {"field": "tier"},
            },
            {
                "type": "points",
                "source_id": "Q_STORES",
                "lat": "lat",
                "lng": "lng",
                "label": "store",
                "tooltip": ["status"],
                "color": {"field": "status"},
            },
        ],
    )


def _cypher_graph_result() -> ResultCardInput:
    df = pd.DataFrame(
        {
            "p": [
                "(:Person {name: 'Alice'})-[:ACTED_IN {role: 'Analyst'}]->(:Movie {title: 'The Matrix'})",
                "(:Person {name: 'Bob'})-[:DIRECTED]->(:Movie {title: 'The Matrix'})",
            ]
        }
    )
    graph = GraphResult.model_validate(
        {
            "nodes": [
                {
                    "id": "person:alice",
                    "label": "Alice",
                    "group": "Person",
                    "properties": {"name": "Alice", "born": 1988},
                },
                {
                    "id": "person:bob",
                    "label": "Bob",
                    "group": "Person",
                    "properties": {"name": "Bob", "born": 1975},
                },
                {
                    "id": "movie:matrix",
                    "label": "The Matrix",
                    "group": "Movie",
                    "properties": {"title": "The Matrix", "released": 1999},
                },
            ],
            "edges": [
                {
                    "id": "rel:alice-acted-in-matrix",
                    "source": "person:alice",
                    "target": "movie:matrix",
                    "label": "ACTED_IN",
                    "directed": True,
                    "properties": {"role": "Analyst"},
                },
                {
                    "id": "rel:bob-directed-matrix",
                    "source": "person:bob",
                    "target": "movie:matrix",
                    "label": "DIRECTED",
                    "directed": True,
                },
            ],
        }
    )
    return _result_input(
        result_id="QDEBUG_CYPHER_GRAPH",
        label="cypher_path_result",
        query="MATCH p=(:Person)-[r]->(:Movie) RETURN p LIMIT 2",
        df=df,
        graph=graph,
        query_lexer="cypher",
    )


def _cypher_non_graph_result() -> ResultCardInput:
    return _result_input(
        result_id="QDEBUG_CYPHER_TABLE",
        label="cypher_scalar_result",
        query=(
            "MATCH (m:Movie)<-[:ACTED_IN]-(p:Person)\n"
            "RETURN m.title AS movie, count(p) AS actor_count\n"
            "ORDER BY actor_count DESC\n"
            "LIMIT 3"
        ),
        df=pd.DataFrame(
            {
                "movie": ["The Matrix", "Inception", "Arrival"],
                "actor_count": [42, 28, 17],
            }
        ),
        query_lexer="cypher",
    )


def _graph_network_card(pane_dir: Path) -> PaneCard:
    nodes = pd.DataFrame(
        [
            {
                "id": "alice",
                "name": "Alice Research Program Coordinator",
                "team": "Research",
                "score": 94,
                "profile": "https://example.com/people/alice",
            },
            {"id": "bob", "name": "Bob", "team": "Research", "score": 78, "profile": "https://example.com/people/bob"},
            {
                "id": "carol",
                "name": "Carol Enterprise Product Strategy Lead",
                "team": "Product",
                "score": 88,
                "profile": "https://example.com/people/carol",
            },
            {"id": "dina", "name": "Dina", "team": "Design", "score": 70, "profile": "https://example.com/people/dina"},
            {"id": "eli", "name": "Eli", "team": "Data", "score": 82, "profile": "https://example.com/people/eli"},
            {"id": "faye", "name": "Faye", "team": "Data", "score": 66, "profile": "https://example.com/people/faye"},
        ]
    )
    edges = pd.DataFrame(
        [
            {
                "src": "alice",
                "dst": "bob",
                "rel": "coauthors",
                "weight": 5,
                "doc": "https://example.com/relations/coauthors",
            },
            {
                "src": "alice",
                "dst": "carol",
                "rel": "advises",
                "weight": 3,
                "doc": "https://example.com/relations/advises",
            },
            {
                "src": "bob",
                "dst": "dina",
                "rel": "reviews",
                "weight": 2,
                "doc": "https://example.com/relations/reviews",
            },
            {
                "src": "carol",
                "dst": "eli",
                "rel": "partners",
                "weight": 4,
                "doc": "https://example.com/relations/partners",
            },
            {
                "src": "eli",
                "dst": "faye",
                "rel": "mentors",
                "weight": 2,
                "doc": "https://example.com/relations/mentors",
            },
            {"src": "faye", "dst": "alice", "rel": "syncs", "weight": 1, "doc": "https://example.com/relations/syncs"},
        ]
    )
    return _graph_card(
        graph_id="GRAPHDEBUG_NETWORK",
        label="force_layout",
        pane_dir=pane_dir,
        sources={"Q_GRAPH_NODES": nodes, "Q_GRAPH_EDGES": edges},
        graph_spec={
            "title": "Collaboration network",
            "layout": "force",
            "nodes": [
                {
                    "source_id": "Q_GRAPH_NODES",
                    "id": "id",
                    "label": "name",
                    "group": "team",
                    "tooltip": ["team", "score", "profile"],
                }
            ],
            "edges": [
                {
                    "source_id": "Q_GRAPH_EDGES",
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                    "tooltip": ["weight", "doc"],
                }
            ],
        },
    )


def _graph_properties_card(pane_dir: Path) -> PaneCard:
    long_text = (
        "This is an intentionally very long property value used to stress graph detail rendering. "
        "It should truncate inside the tooltip without breaking layout, hiding links, or pushing the "
        "popup outside the visible graph viewport. The full value remains in the graph payload and in "
        "the browser title attribute for inspection. "
        "This repeated clause makes the value exceed the graph detail truncation threshold by a wide "
        "margin so the ellipsis should be visible in the rich property graph preview."
    )
    neo4j_property_examples = {
        "string_value": "Neo4j property string",
        "long_string_value": long_text,
        "integer_value": 9_223_372_036_854_775_807,
        "negative_integer_value": -42,
        "float_value": 3.141592653589793,
        "boolean_value": True,
        "date_value": "2026-07-09",
        "local_time_value": "14:35:20.123",
        "time_value": "14:35:20.123-07:00",
        "local_datetime_value": "2026-07-09T14:35:20.123",
        "datetime_value": "2026-07-09T14:35:20.123-07:00[America/Los_Angeles]",
        "duration_value": "P1Y2M3DT4H5M6.789S",
        "point_cartesian_2d": "point({x: 12.5, y: -3.75})",
        "point_cartesian_3d": "point({x: 12.5, y: -3.75, z: 8.0})",
        "point_wgs84_2d": "point({longitude: -122.4194, latitude: 37.7749})",
        "point_wgs84_3d": "point({longitude: -122.4194, latitude: 37.7749, height: 15.2})",
        "byte_array_hex_preview": "0x6e656f346a2d6279746573",
        "string_list": ["graph", "tooltip", "property"],
        "integer_list": [1, 2, 3, 5, 8, 13],
        "float_list": [0.1, 0.25, 0.5, 0.75],
        "boolean_list": [True, False, True],
        "temporal_list": ["2026-07-09", "2026-07-10", "2026-07-11"],
        "point_list": [
            "point({longitude: -122.4194, latitude: 37.7749})",
            "point({longitude: -73.9857, latitude: 40.7484})",
        ],
        "null_renderer_stress": None,
    }
    node_stress_props = {
        f"node_property_{i:02d}": (
            f"{long_text} Field {i}." if i % 5 == 0 else {"rank": i, "flags": [f"flag_{i}", f"flag_{i + 1}"]}
        )
        for i in range(1, 31)
    }
    edge_stress_props = {
        f"relationship_property_{i:02d}": (
            [f"evidence_{i}", f"evidence_{i + 1}", f"{long_text} Edge field {i}."] if i % 6 == 0 else i / 10
        )
        for i in range(1, 31)
    }
    nodes = [
        {
            "id": "person",
            "label": "Person With Rich Properties",
            "group": "Person",
            "age": 36,
            "active": True,
            "aliases": ["Al", "A. Rivera", "Research Lead"],
            "profile": {
                "city": "Oakland",
                "skills": ["graphs", "cypher", "evaluation"],
                "links": {"homepage": "https://example.com/alice", "docs": "https://example.com/docs/alice"},
            },
            "joined": "2021-04-18",
            "notes": "Long node note intended to verify that detailed graph tooltips can carry larger property values.",
            **neo4j_property_examples,
            **node_stress_props,
        },
        {
            "id": "paper",
            "label": "Paper",
            "group": "Artifact",
            "year": 2025,
            "keywords": ["graph rendering", "tooltips", "inspection"],
            "metrics": {"citations": 42, "downloads": 1380, "featured": False},
            "url": "https://example.com/papers/graph-tooltips",
        },
        {
            "id": "team",
            "label": "Team",
            "group": "Org",
            "members": 8,
            "regions": ["US", "EU", "APAC"],
            "metadata": {"budget": "research", "priority": 2},
        },
    ]
    edges = [
        {
            "src": "person",
            "dst": "paper",
            "rel": "AUTHORED",
            "weight": 0.92,
            "roles": ["lead author", "reviewer"],
            "period": {"start": "2024-10-01", "end": "2025-02-14"},
            "evidence": "https://example.com/evidence/authored",
            **edge_stress_props,
        },
        {
            "src": "person",
            "dst": "team",
            "rel": "MEMBER_OF",
            "since": "2020-06-01",
            "allocation": {"research": 0.7, "support": 0.3},
            "flags": ["primary", "remote"],
        },
        {
            "src": "team",
            "dst": "paper",
            "rel": "SPONSORS",
            "approved": True,
            "reviewers": ["Dana", "Eli", "Morgan"],
            "metadata": {"cycle": "Q2", "risk": "low"},
        },
    ]
    return _graph_card(
        graph_id="GRAPHDEBUG_PROPERTIES",
        label="rich_properties",
        pane_dir=pane_dir,
        sources={},
        graph_spec={
            "title": "Rich property graph",
            "layout": "force",
            "nodes": [{"data": nodes, "id": "id", "label": "label", "group": "group", "tooltip": True}],
            "edges": [
                {
                    "data": edges,
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                    "tooltip": True,
                }
            ],
        },
    )


def _physics_graph_card(
    pane_dir: Path,
    *,
    shape: str,
    physics: str,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> PaneCard:
    return _graph_card(
        graph_id=f"GRAPHDEBUG_{shape.upper()}_{physics.upper()}",
        label=f"{physics}_{shape}",
        pane_dir=pane_dir,
        sources={f"Q_{shape.upper()}_NODES": nodes, f"Q_{shape.upper()}_EDGES": edges},
        graph_spec={
            "title": f"{shape.replace('_', ' ').title()} ({physics})",
            "layout": "force",
            "nodes": [
                {
                    "source_id": f"Q_{shape.upper()}_NODES",
                    "id": "id",
                    "label": "label",
                    "group": "group",
                    "tooltip": ["group"],
                }
            ],
            "edges": [
                {
                    "source_id": f"Q_{shape.upper()}_EDGES",
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                }
            ],
        },
    )


def _physics_social_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.DataFrame(
        [
            {"id": "alice", "label": "Alice", "group": "Research"},
            {"id": "bob", "label": "Bob Research Operations Liaison", "group": "Research"},
            {"id": "dina", "label": "Dina", "group": "Design"},
            {"id": "eli", "label": "Eli", "group": "Data"},
            {"id": "faye", "label": "Faye", "group": "Data"},
            {"id": "grace", "label": "Grace", "group": "Product"},
            {"id": "hugo", "label": "Hugo", "group": "Product"},
            {"id": "ivy", "label": "Ivy", "group": "Research"},
            {"id": "jules", "label": "Jules", "group": "Design"},
            {"id": "kai", "label": "Kai", "group": "Data"},
            {"id": "lena", "label": "Lena", "group": "Product"},
            {"id": "mira", "label": "Mira", "group": "Research"},
        ]
    )
    edges = pd.DataFrame(
        [
            {"src": "alice", "dst": "bob", "rel": "coauthors"},
            {"src": "alice", "dst": "dina", "rel": "advises"},
            {"src": "alice", "dst": "faye", "rel": "syncs"},
            {"src": "bob", "dst": "eli", "rel": "reviews"},
            {"src": "bob", "dst": "ivy", "rel": "pairs"},
            {"src": "dina", "dst": "jules", "rel": "designs"},
            {"src": "eli", "dst": "kai", "rel": "mentors"},
            {"src": "faye", "dst": "kai", "rel": "supports"},
            {"src": "grace", "dst": "hugo", "rel": "partners"},
            {"src": "grace", "dst": "lena", "rel": "plans"},
            {"src": "hugo", "dst": "alice", "rel": "briefs"},
            {"src": "ivy", "dst": "mira", "rel": "studies"},
            {"src": "jules", "dst": "grace", "rel": "maps"},
            {"src": "kai", "dst": "mira", "rel": "analyzes"},
            {"src": "lena", "dst": "bob", "rel": "asks"},
            {"src": "mira", "dst": "dina", "rel": "validates"},
        ]
    )
    return nodes, edges


def _physics_chain_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.DataFrame(
        {
            "id": [f"n{i}" for i in range(12)],
            "label": ["Node Six With A Very Long Process Stage Label" if i == 6 else f"N{i}" for i in range(12)],
            "group": ["Chain"] * 12,
        }
    )
    edges = pd.DataFrame(
        [{"src": f"n{i}", "dst": f"n{i + 1}", "rel": "next"} for i in range(11)]
        + [{"src": "n0", "dst": "n6", "rel": "shortcut"}, {"src": "n4", "dst": "n11", "rel": "shortcut"}]
    )
    return nodes, edges


def _physics_disconnected_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = ["Cluster A"] * 7 + ["Cluster B"] * 7
    nodes = pd.DataFrame(
        {
            "id": [f"a{i}" for i in range(7)] + [f"b{i}" for i in range(7)],
            "label": [f"A{i}" for i in range(7)] + [f"B{i}" for i in range(7)],
            "group": groups,
        }
    )
    edges = pd.DataFrame(
        [{"src": "a0", "dst": f"a{i}", "rel": "links"} for i in range(1, 7)]
        + [{"src": "b0", "dst": f"b{i}", "rel": "links"} for i in range(1, 7)]
        + [{"src": "a2", "dst": "a5", "rel": "peer"}, {"src": "b2", "dst": "b5", "rel": "peer"}]
    )
    return nodes, edges


def _physics_dense_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.DataFrame(
        {
            "id": [f"d{i}" for i in range(14)],
            "label": [f"D{i}" for i in range(14)],
            "group": [f"Group {i % 3 + 1}" for i in range(14)],
        }
    )
    edges = []
    for i in range(14):
        edges.append({"src": f"d{i}", "dst": f"d{(i + 1) % 14}", "rel": "ring"})
        edges.append({"src": f"d{i}", "dst": f"d{(i + 4) % 14}", "rel": "chord"})
    return nodes, pd.DataFrame(edges)


def _physics_medium_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    count = 54
    nodes = pd.DataFrame(
        {
            "id": [f"m{i}" for i in range(count)],
            "label": [f"M{i}" for i in range(count)],
            "group": [f"Team {i % 6 + 1}" for i in range(count)],
        }
    )
    edges = []
    for i in range(count):
        edges.append({"src": f"m{i}", "dst": f"m{(i + 1) % count}", "rel": "ring"})
        if i % 2 == 0:
            edges.append({"src": f"m{i}", "dst": f"m{(i + 7) % count}", "rel": "bridge"})
        if i % 5 == 0:
            edges.append({"src": f"m{i}", "dst": f"m{(i + 17) % count}", "rel": "long_link"})
    return nodes, pd.DataFrame(edges)


def _physics_large_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    count = 180
    nodes = pd.DataFrame(
        {
            "id": [f"l{i}" for i in range(count)],
            "label": [f"L{i}" for i in range(count)],
            "group": [f"Squad {i % 9 + 1}" for i in range(count)],
        }
    )
    edges = []
    for i in range(count):
        edges.append({"src": f"l{i}", "dst": f"l{(i + 1) % count}", "rel": "ring"})
        if i % 2 == 0:
            edges.append({"src": f"l{i}", "dst": f"l{(i + 11) % count}", "rel": "bridge"})
        if i % 3 == 0:
            edges.append({"src": f"l{i}", "dst": f"l{(i + 29) % count}", "rel": "long_link"})
        if i % 9 == 0:
            edges.append({"src": f"l{i}", "dst": f"l{(i + 61) % count}", "rel": "cross_cluster"})
    return nodes, pd.DataFrame(edges)


def _physics_xlarge_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    count = 300
    nodes = pd.DataFrame(
        {
            "id": [f"x{i}" for i in range(count)],
            "label": [f"X{i}" for i in range(count)],
            "group": [f"Unit {i % 12 + 1}" for i in range(count)],
        }
    )
    edge_specs: list[tuple[int, int, str]] = []
    for i in range(count):
        edge_specs.append((i, (i + 1) % count, "ring"))
        edge_specs.append((i, (i + 13) % count, "bridge"))
    for i in range(100):
        edge_specs.append((i, (i + 97) % count, "long_link"))
    edges = pd.DataFrame({"src": f"x{src}", "dst": f"x{dst}", "rel": rel} for src, dst, rel in edge_specs)
    return nodes, edges


def _graph_live_physics_stress_cards(pane_dir: Path) -> list[PaneCard]:
    cards: list[PaneCard] = []
    for shape, data_fn in (
        ("social", _physics_social_data),
        ("chain", _physics_chain_data),
        ("disconnected", _physics_disconnected_data),
        ("dense", _physics_dense_data),
        ("medium", _physics_medium_data),
        ("large", _physics_large_data),
        ("xlarge", _physics_xlarge_data),
    ):
        nodes, edges = data_fn()
        cards.append(_physics_graph_card(pane_dir, shape=shape, physics="custom", nodes=nodes, edges=edges))
    return cards


def _graph_lineage_card(pane_dir: Path) -> PaneCard:
    nodes = pd.DataFrame(
        [
            {"id": "raw_events", "label": "Raw Events", "layer": "Raw"},
            {"id": "raw_accounts", "label": "Raw Accounts", "layer": "Raw"},
            {"id": "stg_events", "label": "Stg Events", "layer": "Stage"},
            {"id": "stg_accounts", "label": "Staging Accounts With Long Descriptive Model Name", "layer": "Stage"},
            {"id": "fct_sessions", "label": "Sessions", "layer": "Fact"},
            {"id": "dim_accounts", "label": "Accounts", "layer": "Dimension"},
            {"id": "mart_growth", "label": "Executive Growth Analytics Mart", "layer": "Mart"},
        ]
    )
    edges = pd.DataFrame(
        [
            {"from_id": "raw_events", "to_id": "stg_events", "rel": "feeds"},
            {"from_id": "raw_accounts", "to_id": "stg_accounts", "rel": "feeds"},
            {"from_id": "stg_events", "to_id": "fct_sessions", "rel": "builds"},
            {"from_id": "stg_accounts", "to_id": "dim_accounts", "rel": "builds"},
            {"from_id": "fct_sessions", "to_id": "mart_growth", "rel": "aggregates"},
            {"from_id": "dim_accounts", "to_id": "mart_growth", "rel": "joins"},
        ]
    )
    return _graph_card(
        graph_id="GRAPHDEBUG_LINEAGE",
        label="layered_layout",
        pane_dir=pane_dir,
        sources={"Q_LINEAGE_NODES": nodes, "Q_LINEAGE": edges},
        graph_spec={
            "title": "dbt lineage DAG",
            "layout": "layered",
            "nodes": [
                {
                    "source_id": "Q_LINEAGE_NODES",
                    "id": "id",
                    "label": "label",
                    "group": "layer",
                    "tooltip": ["layer"],
                }
            ],
            "edges": [
                {
                    "source_id": "Q_LINEAGE",
                    "source": "from_id",
                    "target": "to_id",
                    "label": "rel",
                }
            ],
        },
    )


def _graph_tree_card(pane_dir: Path) -> PaneCard:
    nodes = pd.DataFrame(
        [
            {"id": "hq", "label": "HQ", "group": "Org"},
            {"id": "sales", "label": "Sales", "group": "Dept"},
            {"id": "product", "label": "Product Experience And Platform Department", "group": "Dept"},
            {"id": "data", "label": "Data", "group": "Dept"},
            {"id": "east", "label": "East", "group": "Team"},
            {"id": "west", "label": "West", "group": "Team"},
            {"id": "growth", "label": "Growth", "group": "Team"},
            {"id": "platform", "label": "Platform Reliability Enablement Team", "group": "Team"},
            {"id": "analytics", "label": "Analytics", "group": "Team"},
        ]
    )
    edges = pd.DataFrame(
        [
            {"src": "hq", "dst": "sales", "rel": "owns"},
            {"src": "hq", "dst": "product", "rel": "owns"},
            {"src": "hq", "dst": "data", "rel": "owns"},
            {"src": "sales", "dst": "east", "rel": "leads"},
            {"src": "sales", "dst": "west", "rel": "leads"},
            {"src": "product", "dst": "growth", "rel": "leads"},
            {"src": "product", "dst": "platform", "rel": "leads"},
            {"src": "data", "dst": "analytics", "rel": "leads"},
        ]
    )
    return _graph_card(
        graph_id="GRAPHDEBUG_TREE",
        label="tree_layout",
        pane_dir=pane_dir,
        sources={"Q_TREE_NODES": nodes, "Q_TREE_EDGES": edges},
        graph_spec={
            "title": "Org tree",
            "layout": "tree",
            "nodes": [
                {
                    "source_id": "Q_TREE_NODES",
                    "id": "id",
                    "label": "label",
                    "group": "group",
                    "tooltip": ["group"],
                }
            ],
            "edges": [
                {
                    "source_id": "Q_TREE_EDGES",
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                }
            ],
        },
    )


def _wav_bytes(freq_hz: float, seconds: float = 0.4, rate: int = 8000) -> bytes:
    n_samples = int(seconds * rate)
    samples = bytearray()
    amp = 12_000
    for i in range(n_samples):
        samples += struct.pack("<h", int(amp * math.sin(2 * math.pi * freq_hz * i / rate)))
    data_size = len(samples)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", data_size)
    return bytes(header + samples)


def _media_table_result() -> ResultCardInput:
    names = ["red", "green", "blue", "amber", "violet"]
    assets = Path(__file__).parent / "fixtures" / "media"
    jpeg = [assets.joinpath(f"jpeg_{i}.jpg").read_bytes() for i in range(5)]
    gif = [assets.joinpath(f"gif_{i}.gif").read_bytes() for i in range(5)]
    pdf = [assets.joinpath(f"pdf_{i}.pdf").read_bytes() for i in range(5)]
    wav = [
        _wav_bytes(frequency, seconds=duration)
        for frequency, duration in zip(
            (262.0, 294.0, 330.0, 349.0, 392.0),
            (32.0, 38.0, 45.0, 52.0, 60.0),
            strict=True,
        )
    ]
    mp4_bytes = assets.joinpath("sample.mp4").read_bytes()
    jpeg_b64 = [b64encode(blob).decode("ascii") for blob in jpeg]
    df = pd.DataFrame(
        {
            "name": names,
            "jpeg": jpeg,
            "gif": gif,
            "pdf": pdf,
            "wav": wav,
            "mp4": [mp4_bytes for _ in names],
            "jpeg_b64": jpeg_b64,
            "jpeg_data_uri": [f"data:image/jpeg;base64,{payload}" for payload in jpeg_b64],
            "collection": [
                [jpeg[0], gif[0]],
                [jpeg[1], pdf[1], wav[1], mp4_bytes],
                [jpeg[2]],
                [pdf[3], wav[3]],
                [jpeg[4], gif[4], pdf[4], wav[4]],
            ],
            "mixed": [jpeg[0], "plain text", 42, None, "another"],
        }
    )
    return _result_input(
        result_id="QDEBUG_MEDIA",
        label="debug_media",
        query="-- synthetic scalar and collection media payloads (JPEG/GIF/PDF/WAV/MP4)",
        df=df,
    )


def _jpeg_rows_result() -> ResultCardInput:
    assets = Path(__file__).parent / "fixtures" / "media"
    jpeg = [assets.joinpath(f"jpeg_{i}.jpg").read_bytes() for i in range(5)]
    return _result_input(
        result_id="QDEBUG_JPEG_ROWS",
        label="jpeg_rows",
        query="-- 120 synthetic JPEG-only rows",
        df=pd.DataFrame({"jpg_image": [jpeg[i % len(jpeg)] for i in range(120)]}),
    )
