from typing import ClassVar
from dataclasses import dataclass
from mintq.preprocessors.er_diagram import (
    ERDiagram,
    ERDConceptualEntity,
    ERDRelationship,
)


@dataclass
class ERDiagramMermaidFormatter:
    """Formats an ER diagram into Mermaid erDiagram format."""

    name: ClassVar[str] = "er_diagram_mermaid"
    include_source_tables: bool = True
    include_descriptions: bool = True
    include_join_snippets: bool = True

    def format(self, er_diagram: ERDiagram) -> str:
        """Format the complete ER diagram in Mermaid syntax."""
        lines = ["erDiagram"]

        # Format entities with their source tables as attributes
        for entity in er_diagram.conceptual_entities:
            lines.append(self._format_entity(entity))

        # Format relationships (with optional join comments)
        for rel in er_diagram.relationships:
            rel_lines = self._format_relationship(rel)
            if rel_lines:
                lines.append(rel_lines)

        return "```mermaid\n" + "\n".join(lines) + "\n```"

    def _format_entity(self, entity: ERDConceptualEntity) -> str:
        """Format a single entity with its source tables as attributes."""
        lines = []
        entity_name = self._sanitize_name(entity.name)
        lines.append(f"    {entity_name} {{")

        if self.include_source_tables and entity.source_tables:
            for st in entity.source_tables:
                table_name = self._format_table_name(st.table_name, st.schema_name)
                # Use table as "type" and mapping_description as attribute name
                desc = self._sanitize_string(st.mapping_description) if self.include_descriptions else ""
                lines.append(f'        table {table_name} "{desc}"')

        lines.append("    }")
        return "\n".join(lines)

    def _format_table_name(self, table_name: str, schema_name: str | None) -> str:
        """Format a fully qualified table name, sanitized for Mermaid."""
        if schema_name:
            return self._sanitize_name(f"{schema_name}_{table_name}")
        return self._sanitize_name(table_name)

    def _format_relationship(self, rel: ERDRelationship) -> str:
        """Format a relationship line in Mermaid syntax with optional inline join comment."""
        if len(rel.participants) < 2:
            return ""

        # Build join comment suffix
        join_comment = ""
        if self.include_join_snippets and rel.join_sql_snippet:
            join_sql = self._sanitize_comment(rel.join_sql_snippet)
            join_comment = f" %% {join_sql}"

        # For binary relationships, use standard Mermaid ER notation
        if len(rel.participants) == 2:
            p1, p2 = rel.participants[0], rel.participants[1]
            left_card = self._mermaid_cardinality_left(p1.max_cardinality, p1.participation)
            right_card = self._mermaid_cardinality_right(p2.max_cardinality, p2.participation)
            e1 = self._sanitize_name(p1.entity)
            e2 = self._sanitize_name(p2.entity)
            label = self._sanitize_string(rel.name)
            return f'    {e1} {left_card}--{right_card} {e2} : "{label}"{join_comment}'
        else:
            # N-ary relationships: create lines for each pair from first entity
            lines = []
            first = rel.participants[0]
            for i, other in enumerate(rel.participants[1:]):
                left_card = self._mermaid_cardinality_left(first.max_cardinality, first.participation)
                right_card = self._mermaid_cardinality_right(other.max_cardinality, other.participation)
                e1 = self._sanitize_name(first.entity)
                e2 = self._sanitize_name(other.entity)
                label = self._sanitize_string(f"{rel.name}_{other.role}")
                # Only add join comment to the first line for n-ary relationships
                comment = join_comment if i == 0 else ""
                lines.append(f'    {e1} {left_card}--{right_card} {e2} : "{label}"{comment}')
            return "\n".join(lines)

    def _mermaid_cardinality_left(self, max_cardinality: str, participation: str) -> str:
        """
        Return Mermaid left-side cardinality notation.
        Mermaid uses: || (exactly one), |o (zero or one), }| (one or more), }o (zero or more)
        """
        if max_cardinality == "one":
            return "||" if participation == "mandatory" else "|o"
        else:
            return "}|" if participation == "mandatory" else "}o"

    def _mermaid_cardinality_right(self, max_cardinality: str, participation: str) -> str:
        """
        Return Mermaid right-side cardinality notation.
        Mermaid uses: || (exactly one), o| (zero or one), |{ (one or more), o{ (zero or more)
        """
        if max_cardinality == "one":
            return "||" if participation == "mandatory" else "o|"
        else:
            return "|{" if participation == "mandatory" else "o{"

    def _sanitize_name(self, name: str) -> str:
        """Sanitize entity/attribute names for Mermaid (no spaces, special chars)."""
        # Replace problematic characters
        result = name.replace(" ", "_").replace("-", "_").replace(".", "_")
        # Remove any remaining non-alphanumeric chars except underscore
        result = "".join(c if c.isalnum() or c == "_" else "" for c in result)
        return result

    def _sanitize_string(self, s: str) -> str:
        """Sanitize a string for use in Mermaid labels (escape quotes)."""
        return s.replace('"', "'").replace("\n", " ")

    def _sanitize_comment(self, s: str) -> str:
        """Sanitize a string for use in Mermaid comments (single line)."""
        return s.replace("\n", " ").strip()
