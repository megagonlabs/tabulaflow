from typing import ClassVar, Literal
from dataclasses import dataclass
from mintq.preprocessors.er_diagram import (
    ERDiagram,
    ERDConceptualEntity,
    ERDRelationship,
    ERDRelationshipParticipant,
    EntitySourceTable,
)


@dataclass
class ERDiagramFormatter:
    """Formats an ER diagram into a human-readable text representation."""

    name: ClassVar[str] = "er_diagram"
    format_style: Literal["markdown", "plain"] = "markdown"
    include_join_snippets: bool = True
    include_source_tables: bool = True

    def format(self, er_diagram: ERDiagram) -> str:
        """Format the complete ER diagram."""
        sections = []

        if self.format_style == "markdown":
            sections.append("# ER Diagram")
        else:
            sections.append("ER DIAGRAM")
            sections.append("=" * 40)

        # Format entities
        sections.append(self._format_entities_section(er_diagram.conceptual_entities))

        # Format relationships
        sections.append(self._format_relationships_section(er_diagram.relationships))

        return "\n\n".join(sections)

    def _format_entities_section(self, entities: list[ERDConceptualEntity]) -> str:
        """Format the entities section."""
        lines = []

        if self.format_style == "markdown":
            lines.append("## Entities")
        else:
            lines.append("ENTITIES")
            lines.append("-" * 40)

        for entity in entities:
            lines.append("")
            lines.append(self._format_entity(entity))

        return "\n".join(lines)

    def _format_entity(self, entity: ERDConceptualEntity) -> str:
        """Format a single conceptual entity."""
        lines = []

        if self.format_style == "markdown":
            lines.append(f"### {entity.name}")
            lines.append(f"{entity.description}")
        else:
            lines.append(f"[{entity.name}]")
            lines.append(f"  Description: {entity.description}")

        if self.include_source_tables and entity.source_tables:
            lines.append("")
            lines.append(self._format_source_tables(entity.source_tables))

        return "\n".join(lines)

    def _format_source_tables(self, source_tables: list[EntitySourceTable]) -> str:
        """Format the source tables for an entity."""
        lines = []

        if self.format_style == "markdown":
            lines.append("**Source Tables:**")
            for st in source_tables:
                table_name = self._format_table_name(st.table_name, st.schema_name)
                lines.append(f"- `{table_name}`: {st.mapping_description}")
        else:
            lines.append("  Source Tables:")
            for st in source_tables:
                table_name = self._format_table_name(st.table_name, st.schema_name)
                lines.append(f"    - {table_name}: {st.mapping_description}")

        return "\n".join(lines)

    def _format_table_name(self, table_name: str, schema_name: str | None) -> str:
        """Format a fully qualified table name."""
        if schema_name:
            return f"{schema_name}.{table_name}"
        return table_name

    def _format_relationships_section(self, relationships: list[ERDRelationship]) -> str:
        """Format the relationships section."""
        lines = []

        if self.format_style == "markdown":
            lines.append("## Relationships")
        else:
            lines.append("RELATIONSHIPS")
            lines.append("-" * 40)

        if not relationships:
            lines.append("")
            lines.append("(No relationships defined)")
            return "\n".join(lines)

        for relationship in relationships:
            lines.append("")
            lines.append(self._format_relationship(relationship))

        return "\n".join(lines)

    def _format_relationship(self, relationship: ERDRelationship) -> str:
        """Format a single relationship."""
        lines = []

        if self.format_style == "markdown":
            lines.append(f"### {relationship.name}")
            lines.append(f"{relationship.description}")
            lines.append("")
            lines.append("**Participants:**")
            for participant in relationship.participants:
                lines.append(self._format_participant_markdown(participant))
            if self.include_join_snippets:
                lines.append("")
                lines.append(f"**Join:** `{relationship.join_sql_snippet}`")
        else:
            lines.append(f"[{relationship.name}]")
            lines.append(f"  Description: {relationship.description}")
            lines.append("  Participants:")
            for participant in relationship.participants:
                lines.append(self._format_participant_plain(participant))
            if self.include_join_snippets:
                lines.append(f"  Join: {relationship.join_sql_snippet}")

        return "\n".join(lines)

    def _format_participant_markdown(self, participant: ERDRelationshipParticipant) -> str:
        """Format a relationship participant in markdown style."""
        cardinality = self._format_cardinality(participant.max_cardinality, participant.participation)
        return f"- **{participant.entity}** ({participant.role}): {cardinality}"

    def _format_participant_plain(self, participant: ERDRelationshipParticipant) -> str:
        """Format a relationship participant in plain text style."""
        cardinality = self._format_cardinality(participant.max_cardinality, participant.participation)
        return f"    - {participant.entity} ({participant.role}): {cardinality}"

    def _format_cardinality(self, max_cardinality: str, participation: str) -> str:
        """Format cardinality notation (e.g., '1', '0..1', '1..*', '0..*')."""
        min_card = "1" if participation == "mandatory" else "0"
        max_card = "1" if max_cardinality == "one" else "*"

        if min_card == max_card:
            return min_card
        return f"{min_card}..{max_card}"


@dataclass
class ERDiagramCompactFormatter:
    """Formats an ER diagram into a compact notation suitable for LLM context."""

    name: ClassVar[str] = "er_diagram_compact"
    include_source_tables: bool = False

    def format(self, er_diagram: ERDiagram) -> str:
        """Format the ER diagram in compact notation."""
        lines = []

        # Entities section
        lines.append("Entities:")
        for entity in er_diagram.conceptual_entities:
            lines.append(self._format_entity_compact(entity))

        lines.append("")

        # Relationships section
        lines.append("Relationships:")
        for rel in er_diagram.relationships:
            lines.append(self._format_relationship_compact(rel))

        return "\n".join(lines)

    def _format_entity_compact(self, entity: ERDConceptualEntity) -> str:
        """Format entity in compact form: EntityName - description [tables]."""
        parts = [f"  {entity.name}"]

        if entity.description:
            # Truncate description if too long
            desc = entity.description
            if len(desc) > 80:
                desc = desc[:77] + "..."
            parts.append(f" - {desc}")

        if self.include_source_tables and entity.source_tables:
            table_names = [
                self._format_table_name(st.table_name, st.schema_name) for st in entity.source_tables
            ]
            parts.append(f" [{', '.join(table_names)}]")

        return "".join(parts)

    def _format_table_name(self, table_name: str, schema_name: str | None) -> str:
        """Format a fully qualified table name."""
        if schema_name:
            return f"{schema_name}.{table_name}"
        return table_name

    def _format_relationship_compact(self, rel: ERDRelationship) -> str:
        """Format relationship in compact notation: Entity1 --cardinality-- Entity2."""
        if len(rel.participants) == 2:
            p1, p2 = rel.participants[0], rel.participants[1]
            card1 = self._cardinality_symbol(p1.max_cardinality, p1.participation)
            card2 = self._cardinality_symbol(p2.max_cardinality, p2.participation)
            return f"  {p1.entity} {card1}--{rel.name}--{card2} {p2.entity}"
        else:
            # N-ary relationship
            participants_str = ", ".join(
                f"{p.entity}({self._cardinality_symbol(p.max_cardinality, p.participation)})"
                for p in rel.participants
            )
            return f"  {rel.name}: {participants_str}"

    def _cardinality_symbol(self, max_cardinality: str, participation: str) -> str:
        """Return compact cardinality symbol."""
        if max_cardinality == "one":
            return "1" if participation == "mandatory" else "0..1"
        else:
            return "1..*" if participation == "mandatory" else "*"
