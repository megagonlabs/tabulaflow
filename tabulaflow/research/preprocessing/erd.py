"""Conceptual ER-diagram synthesis for research preprocessing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

import jinja2
from pydantic import BaseModel, Field
from pydantic_ai.settings import ModelSettings

from tabulaflow.agents._cache import load_or_compute_model
from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.runtime import _get_agent_runtime
from tabulaflow.agents.tools.run_query import RunQueryTool
from tabulaflow.agents.trace import Usage
from tabulaflow.core._cache import stable_cache_key
from tabulaflow.core import SQLSchema, TableRef
from tabulaflow.data import SQLConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter, SQLSchemaFormatter
from tabulaflow.research.preprocessing.registry import preprocessor_registry


class EntitySourceTable(BaseModel):
    schema_name: str | None
    table_name: str
    mapping_description: str = Field(
        description="A concise sentence description of what information is stored in the table."
    )


class ERDConceptualEntity(BaseModel):
    name: str = Field(description="The name of the conceptual entity, in PascalCase.")
    description: str = Field(description="A 1-2 sentence description of the conceptual entity.")
    source_tables: list[EntitySourceTable]


class ERDRelationshipParticipant(BaseModel):
    """A participant entity in a relationship with its cardinality."""

    entity: str
    role: str
    max_cardinality: Literal["one", "many"]
    participation: Literal["mandatory", "optional"]


class ERDRelationship(BaseModel):
    name: str = Field(description="The name of the relationship, in PascalCase.")
    description: str = Field(description="A 1-2 sentence description of the relationship.")
    participants: list[ERDRelationshipParticipant] = Field(description="The participants in the n-ary relationship.")
    join_sql_snippet: str = Field(
        description="The SQL snippet to join the participants. Should include all participating tables. Example: `FROM table1 JOIN table2 ON table1.id = table2.id`"
    )


class ERDiagram(BaseModel):
    conceptual_entities: list[ERDConceptualEntity]
    relationships: list[ERDRelationship]

    def trim(self, table_refs: list[TableRef], case_insensitive: bool = True) -> "ERDiagram":
        """Trim the ER diagram to only include entities and relationships relevant to the given tables."""

        def normalize(s: str | None) -> str | None:
            return s.lower() if s is not None and case_insensitive else s

        # Convert table_refs to a set of (schema_name, table_name) tuples for fast lookup
        table_ref_set = {(normalize(ref.schema_name), normalize(ref.table_name)) for ref in table_refs}

        # Keep entities that have at least one source table in the given table_refs
        kept_entities: list[ERDConceptualEntity] = []
        kept_entity_names: set[str] = set()
        for entity in self.conceptual_entities:
            for source_table in entity.source_tables:
                if (normalize(source_table.schema_name), normalize(source_table.table_name)) in table_ref_set:
                    kept_entities.append(entity)
                    kept_entity_names.add(entity.name)
                    break

        # Keep relationships where all participants are in the kept entities
        kept_relationships: list[ERDRelationship] = []
        for relationship in self.relationships:
            if all(p.entity in kept_entity_names for p in relationship.participants):
                kept_relationships.append(relationship)

        return ERDiagram(conceptual_entities=kept_entities, relationships=kept_relationships)


@dataclass
class MermaidERDiagramFormatter:
    """Formats an ER diagram into Mermaid erDiagram format."""

    name: ClassVar[str] = "er_diagram_mermaid"
    include_source_tables: bool = True
    include_descriptions: bool = True
    include_relation_descriptions: bool = True
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
                lines.append("\n" + rel_lines)

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
            return self._sanitize_name(f"{schema_name}__{table_name}")
        return self._sanitize_name(table_name)

    def _format_relationship(self, rel: ERDRelationship) -> str:
        """Format a relationship line in Mermaid syntax with optional join comment above."""
        if len(rel.participants) < 2:
            return ""

        lines = []

        # For binary relationships, use standard Mermaid ER notation
        if len(rel.participants) == 2:
            p1, p2 = rel.participants[0], rel.participants[1]
            left_card = self._mermaid_cardinality_left(p1.max_cardinality, p1.participation)
            right_card = self._mermaid_cardinality_right(p2.max_cardinality, p2.participation)
            e1 = self._sanitize_name(p1.entity)
            e2 = self._sanitize_name(p2.entity)
            label = self._sanitize_string(rel.name)
            lines.append(f'    {e1} {left_card}--{right_card} {e2} : "{label}"')
        else:
            # N-ary relationships: create lines for each pair from first entity
            first = rel.participants[0]
            for other in rel.participants[1:]:
                left_card = self._mermaid_cardinality_left(first.max_cardinality, first.participation)
                right_card = self._mermaid_cardinality_right(other.max_cardinality, other.participation)
                e1 = self._sanitize_name(first.entity)
                e2 = self._sanitize_name(other.entity)
                label = self._sanitize_string(f"{rel.name}_{other.role}")
                lines.append(f'    {e1} {left_card}--{right_card} {e2} : "{label}"')

        # Add relation description as a Mermaid comment
        if self.include_relation_descriptions and rel.description:
            desc = self._sanitize_comment(rel.description)
            lines.append(f"    %% {desc}")

        # Add join SQL as a Mermaid comment on its own line (inline comments break GitHub renderer)
        if self.include_join_snippets and rel.join_sql_snippet:
            join_sql = self._sanitize_comment(rel.join_sql_snippet)
            lines.append(f"    %% SQL join path: `{join_sql}`")

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


ER_DIAGRAM_SYNTHESIS_PROMPT = """
You are an AI database expert tasked with generating an ER diagram given a physical database schema.

<entities_requirements>
- Model conceptual entities (business nouns), each mapped to one or more physical tables.
- Common mapping cases when choosing conceptual_entities and source_tables:
  1) One conceptual entity <-> one table
     - Note that if the entity has other attributes stored in a separate table (vertical partitioning), you should follow case 2) and consider them as one entity.
  2) One conceptual entity <-> multiple tables (vertical partitioning / extension tables / inheritance / history split):
     - Include multiple EntitySourceTable entries under the same conceptual entity.
     - mapping_description must explain the partitioning (e.g., “core columns”, “extended profile fields”, “SCD history records”).
     - Example: A "User" entity mapped to both `users` (core info) and `profiles` (extended attributes).
</entities_requirements>

<relationships_requirements>
- Model relationships as associations between conceptual entities with clear meaning, cardinality, and optionality.
- Common mapping cases:
  1) 1-to-1 or 1-to-many implemented by FK or non-enforced columns:
     - For self-relationships, entity participates twice with distinct roles, e.g., manager vs report).
  2) junction table:
     - join_sql_snippet MUST include the junction table JOINs.
- join_sql_snippet should support cases where column transformations are needed (e.g., type casts, string functions, JSON extraction)
</relationships_requirements>

<granularity_level>
- Produce an ER diagram at the CONCEPTUAL-ENTITY level, where each conceptual entity maps to at least one PHYSICAL TABLE via source_tables.
- Avoid creating overly abstract entities that do not correspond to any table.
</granularity_level>

<entity_order>
- Output conceptual_entities in a readable, stable order using this algorithm:
  1) If the ER graph has multiple disconnected components, output components separately (largest component first), without mixing.
  2) Within each component, group entities by domain/module if clearly implied by naming/schema (e.g., auth.*, billing.*, catalog.*).
     If not clear, skip module grouping.
  3) Within each (component, module) group:
     a) "Anchor" entities first: entities with the highest relationship degree (most relationships).
     b) Then parent-before-child preference using relationship semantics:
        - for 1-to-many, put the "one" side before the "many" side
        - for identifying/dependent patterns, owner before dependent
</entity_order>
"""


def format_user_prompt(schema: SQLSchema, formatter: SQLSchemaFormatter) -> str:
    return "Generate the conceptual ER diagram for the following physical database schema:\n" + formatter.format(
        schema, include_descriptions=False
    )


@preprocessor_registry.register
class ERDiagramSynthesizer:
    name: ClassVar[str] = "er_diagram_synthesizer"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"

    def __init__(
        self,
        llm: str = "openai-responses:gpt-5",
        model_settings: ModelSettings | None = None,
    ):
        self.llm = llm
        self.model_settings = model_settings
        self.formatter = SQLDDLSchemaFormatter(compact_table_families=True)
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    def _cache_path(self, cache_dir: Path, connector: SQLConnector) -> Path:
        key = stable_cache_key(
            {
                "version": "v1",
                "global_id": connector.global_id,
                "schema": connector.schema.model_dump(mode="json"),
                "llm": self.llm,
                "model_settings": self.model_settings,
            }
        )
        return cache_dir / "agent" / "er_diagrams" / f"v1@{key}.json"

    async def preprocess_async(self, connector: SQLConnector) -> ERDiagram:
        config = _get_agent_runtime().config
        return await load_or_compute_model(
            path=self._cache_path(config.cache_dir, connector),
            mode=config.preprocessing_cache_mode,
            model_type=ERDiagram,
            compute=lambda: self._synthesize(connector),
        )

    async def _synthesize(self, db_connector: SQLConnector) -> ERDiagram:
        schema = db_connector.schema

        system_prompt = jinja2.Template(ER_DIAGRAM_SYNTHESIS_PROMPT).render()
        run_query_tool = RunQueryTool(db_connector)
        agent = make_agent(
            self.llm,
            output_type=ERDiagram,
            instructions=system_prompt,
            tools=[run_query_tool.as_pydantic_ai_tool()],
            model_settings=self.model_settings,
        )
        user_prompt = format_user_prompt(schema, self.formatter)
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage, self.llm)
        erd = result.output
        # Sometimes LLM put database name as the schema name, remove it if the database does not have any schema names
        if all(table.schema_name is None for table in schema.tables):
            for entity in erd.conceptual_entities:
                for source_table in entity.source_tables:
                    source_table.schema_name = None
        return erd
