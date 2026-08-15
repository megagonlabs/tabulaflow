from typing import ClassVar
from dataclasses import dataclass

from tabulaflow.output.schema_formatters.base import schema_formatter_registry
from tabulaflow.core import GraphPropertySchema, NodeSchema, PropertyGraphSchema, RelationshipSchema


@schema_formatter_registry.register
@dataclass
class CypherSchemaFormatter:
    """Formats a property-graph schema using the Neo4j-standard Text2Cypher representation.

    Example output::

        Database: movies (Query Language: cypher)

        Node properties:
        Person {name: STRING, born: INTEGER}
        Movie {title: STRING, released: INTEGER, tagline: STRING}

        The relationships:
        (:Person)-[:ACTED_IN]->(:Movie)
        (:Person)-[:DIRECTED]->(:Movie)

        Relationship properties:
        ACTED_IN {roles: LIST OF STRING}
    """

    name: ClassVar[str] = "cypher"

    def format(self, schema: PropertyGraphSchema) -> str:
        def _section(title: str, lines: list[str]) -> str:
            return "\n".join([title] + (lines or ["(none)"]))

        node_lines = [self._format_node(n) for n in schema.nodes]
        rel_lines = [
            self._format_pattern(rel.label, endpoint.source_label, endpoint.target_label)
            for rel in schema.relationships
            for endpoint in rel.endpoints
        ]
        rel_prop_lines = self._format_relationship_properties(schema.relationships)

        header = f"Database: {schema.name} (Query Language: cypher)"
        if schema.description:
            header += f"\nDescription: {schema.description}"

        return "\n\n".join(
            [
                header,
                _section("Node properties:", node_lines),
                _section("The relationships:", rel_lines),
                _section("Relationship properties:", rel_prop_lines),
            ]
        )

    def _format_node(self, node: NodeSchema) -> str:
        line = node.label
        if node.properties:
            line += " {" + ", ".join(self._format_property(p) for p in node.properties) + "}"
        if node.description:
            line += f"  // {node.description}"
        return line

    def _format_pattern(self, label: str, source_label: str, target_label: str) -> str:
        return f"(:{source_label})-[:{label}]->(:{target_label})"

    def _format_property(self, prop: GraphPropertySchema) -> str:
        return f"{prop.name}: {prop.dtype}"

    def _format_relationship_properties(self, relationships: list[RelationshipSchema]) -> list[str]:
        lines: list[str] = []
        for rel in relationships:
            if not (rel.properties or rel.description):
                continue
            line = rel.label
            if rel.properties:
                line += " {" + ", ".join(self._format_property(p) for p in rel.properties) + "}"
            if rel.description:
                line += f"  // {rel.description}"
            lines.append(line)
        return lines
