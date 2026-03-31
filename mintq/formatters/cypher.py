from typing import ClassVar
from dataclasses import dataclass

from mintq.formatters.base import formatter_registry
from mintq.schema import (
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

    def format(
        self,
        schema: PropertyGraphSchema,
        add_description: bool = False,
    ) -> str:
        header = f"Database: {schema.name} (Query Language: cypher)"

        node_lines = [self.format_node(n, add_description) for n in schema.nodes]
        rel_prop_lines = self._format_relationship_properties(schema.relationships, add_description)
        rel_pattern_lines = [self.format_relationship(r) for r in schema.relationships]

        parts = [header]

        node_section = ["Node properties:"] + (node_lines or ["(none)"])
        rel_prop_section = ["Relationship properties:"] + (rel_prop_lines or ["(none)"])
        rel_section = ["The relationships:"] + (rel_pattern_lines or ["(none)"])

        parts.append("\n".join(node_section))
        parts.append("\n".join(rel_section))
        parts.append("\n".join(rel_prop_section))

        return "\n\n".join(parts)

    def format_node(self, node: NodeSchema, add_description: bool = False) -> str:
        line = node.label
        if node.properties:
            line += " {" + ", ".join(self.format_property(p) for p in node.properties) + "}"
        if add_description and node.description:
            line += f"  // {node.description}"
        return line

    def format_relationship(self, rel: RelationshipSchema) -> str:
        return f"(:{rel.source_label})-[:{rel.label}]->(:{rel.target_label})"

    def format_property(self, prop: GraphPropertySchema) -> str:
        return f"{prop.name}: {prop.dtype}"

    def _format_relationship_properties(
        self,
        relationships: list[RelationshipSchema],
        add_description: bool = False,
    ) -> list[str]:
        """Deduplicate relationship properties by label (multiple patterns may share a label)."""
        seen: set[str] = set()
        lines: list[str] = []
        for rel in relationships:
            if rel.label in seen:
                continue
            seen.add(rel.label)
            line = rel.label
            if rel.properties:
                line += " {" + ", ".join(self.format_property(p) for p in rel.properties) + "}"
            if add_description and rel.description:
                line += f"  // {rel.description}"
            lines.append(line)
        return lines
