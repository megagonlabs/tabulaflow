from typing import ClassVar, Literal
from pydantic import BaseModel, Field
import jinja2
from pydantic_ai import Agent
from tabulaflow.core.formatters.base import BaseSQLSchemaFormatter
from tabulaflow.core.preprocessors.components.schema_compressor import SchemaCompressor
from tabulaflow.core.types import SQLSchema, TableRef, Usage
from tabulaflow.core.db_connector import BaseSQLDBConnector
from tabulaflow.core.preprocessors.base import CachedPreprocessorMixin, preprocessor_registry, CacheableResult
from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.core.tools.run_query import RunQueryTool

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


def format_user_prompt(schema: SQLSchema, formatter: BaseSQLSchemaFormatter) -> str:
    return "Generate the conceptual ER diagram for the following physical database schema:\n" + formatter.format(
        schema, add_description=False
    )


@preprocessor_registry.register
class ERDiagramSynthesizer(CachedPreprocessorMixin[ERDiagram]):
    name: ClassVar[str] = "er_diagram_synthesizer"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"
    output_type: ClassVar[type[CacheableResult]] = ERDiagram

    def __init__(self, llm: str = "openai-responses:gpt-5", compress_schema: bool = True):
        self.llm = llm
        self.compressor = SchemaCompressor() if compress_schema else None
        self.formatter = SQLDDLSchemaFormatter()
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    async def _preprocess_impl_async(self, db_connector: BaseSQLDBConnector) -> ERDiagram:
        schema = db_connector.schema
        if self.compressor is not None:
            schema = self.compressor.compress(schema)

        system_prompt = jinja2.Template(ER_DIAGRAM_SYNTHESIS_PROMPT).render()
        run_query_tool = RunQueryTool(db_connector)
        agent = Agent[None, ERDiagram](
            model=self.llm,
            output_type=ERDiagram,
            instructions=system_prompt,
            tools=[run_query_tool.as_pydantic_ai_tool()],
        )
        user_prompt = format_user_prompt(schema, self.formatter)
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        erd = result.output
        # Sometimes LLM put database name as the schema name, remove it if the database does not have any schema names
        if all(table.schema_name is None for table in schema.tables):
            for entity in erd.conceptual_entities:
                for source_table in entity.source_tables:
                    source_table.schema_name = None
        return erd
