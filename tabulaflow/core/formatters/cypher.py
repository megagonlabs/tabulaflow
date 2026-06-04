from typing import ClassVar
from dataclasses import dataclass

from tabulaflow.core.formatters.base import formatter_registry
from tabulaflow.schema import (
    GraphPropertySchema,
    NodeSchema,
    PropertyGraphSchema,
    RelationshipSchema,
)


@formatter_registry.register
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

        node_lines = [self.format_node(n) for n in schema.nodes]
        rel_lines = [self.format_relationship(r) for r in schema.relationships]
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

    def format_node(self, node: NodeSchema) -> str:
        line = node.label
        if node.properties:
            line += " {" + ", ".join(self.format_property(p) for p in node.properties) + "}"
        if node.description:
            line += f"  // {node.description}"
        return line

    def format_relationship(self, rel: RelationshipSchema) -> str:
        return f"(:{rel.source_label})-[:{rel.label}]->(:{rel.target_label})"

    def format_property(self, prop: GraphPropertySchema) -> str:
        return f"{prop.name}: {prop.dtype}"

    def _format_relationship_properties(self, relationships: list[RelationshipSchema]) -> list[str]:
        """Deduplicate relationship properties by label (multiple patterns may share a label)."""
        seen: set[str] = set()
        lines: list[str] = []
        for rel in relationships:
            if rel.label in seen or not (rel.properties or rel.description):
                continue
            seen.add(rel.label)
            line = rel.label
            if rel.properties:
                line += " {" + ", ".join(self.format_property(p) for p in rel.properties) + "}"
            if rel.description:
                line += f"  // {rel.description}"
            lines.append(line)
        return lines
