from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.widgets import Tree

from tabulaflow.app.screens import SchemaBrowserScreen
from tabulaflow.data import DBRegistry
from tabulaflow.core import (
    ExecResult,
    GraphPropertySchema,
    NodeSchema,
    PropertyGraphSchema,
    RelationshipEndpoint,
    RelationshipSchema,
)


class FakeGraphConnector:
    connector_type = "property_graph"
    backend = "neo4j"
    global_id = "test+neo"
    language = "cypher"

    def __init__(self) -> None:
        self.schema = PropertyGraphSchema(
            name="neo",
            nodes=[
                NodeSchema(
                    label="Movie",
                    properties=[
                        GraphPropertySchema(name="title", dtype="STRING"),
                        GraphPropertySchema(name="released", dtype="INTEGER"),
                    ],
                ),
                NodeSchema(
                    label="Person",
                    properties=[GraphPropertySchema(name="name", dtype="STRING")],
                ),
            ],
            relationships=[
                RelationshipSchema(
                    label="ACTED_IN",
                    endpoints=[RelationshipEndpoint(source_label="Person", target_label="Movie")],
                    properties=[GraphPropertySchema(name="roles", dtype="LIST OF STRING")],
                )
            ],
        )

    async def run_query_async(
        self, query: str, parameters: object | None = None, timeout: int | None = None
    ) -> ExecResult:
        return ExecResult()

    async def disconnect_async(self) -> None:
        pass

    async def refresh_schema_async(self) -> PropertyGraphSchema:
        return self.schema


class SchemaBrowserTestApp(App[None]):
    def __init__(self, registry: DBRegistry) -> None:
        super().__init__()
        self.registry = registry

    def compose(self) -> ComposeResult:
        yield SchemaBrowserScreen(registry=self.registry)


def _tree_label_text(tree: Tree[object]) -> list[str]:
    labels: list[str] = []
    stack = list(tree.root.children)
    while stack:
        node = stack.pop(0)
        label = getattr(node.label, "plain", str(node.label))
        labels.append(label)
        stack[0:0] = list(node.children)
    return labels


def _tree_nodes(tree: Tree[object]) -> list[Any]:
    nodes: list[Any] = []
    stack = list(tree.root.children)
    while stack:
        node = stack.pop(0)
        nodes.append(node)
        stack[0:0] = list(node.children)
    return nodes


def _tree_node_by_label(tree: Tree[object], label: str) -> Any:
    return next(node for node in _tree_nodes(tree) if getattr(node.label, "plain", str(node.label)) == label)


async def test_schema_browser_renders_property_graph_schema() -> None:
    registry = DBRegistry()
    registry.register("neo", FakeGraphConnector())  # type: ignore[arg-type]
    app = SchemaBrowserTestApp(registry)

    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one("#browse-tree", Tree)
        labels = _tree_label_text(tree)

    assert "neo  neo4j" in labels
    assert "Node Types" in labels
    assert "Movie" in labels
    assert "title     STRING" in labels
    assert "Relationship Types" in labels
    assert "ACTED_IN" in labels
    assert "ACTED_IN  Person -> Movie" not in labels
    assert "roles  LIST OF STRING" in labels
    assert not _tree_node_by_label(tree, "neo  neo4j").is_expanded

    title_node = next(
        node
        for node in _tree_nodes(tree)
        if getattr(node.label, "plain", str(node.label)).strip() == "title     STRING"
    )
    assert title_node.data.status_text == "neo > Node Types > Movie > title  |  STRING"

    roles_node = next(
        node
        for node in _tree_nodes(tree)
        if getattr(node.label, "plain", str(node.label)).strip() == "roles  LIST OF STRING"
    )
    assert roles_node.data.status_text == "neo > Relationship Types > ACTED_IN > roles  |  LIST OF STRING"


def test_cypher_formatter_renders_multi_endpoint_relationship_type_once() -> None:
    from tabulaflow.output.schema_formatters.cypher import CypherSchemaFormatter

    schema = PropertyGraphSchema(
        name="places",
        relationships=[
            RelationshipSchema(
                label="LOCATED_IN",
                endpoints=[
                    RelationshipEndpoint(source_label="City", target_label="Country"),
                    RelationshipEndpoint(source_label="Landmark", target_label="Country"),
                ],
                properties=[GraphPropertySchema(name="since", dtype="INTEGER")],
            )
        ],
    )

    formatted = CypherSchemaFormatter().format(schema)

    assert "(:City)-[:LOCATED_IN]->(:Country)" in formatted
    assert "(:Landmark)-[:LOCATED_IN]->(:Country)" in formatted
    assert formatted.count("LOCATED_IN {since: INTEGER}") == 1
