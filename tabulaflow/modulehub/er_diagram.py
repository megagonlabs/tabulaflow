from typing import ClassVar, Literal

import jinja2

from tabulaflow.core.db_connector import BaseSQLDBConnector
from tabulaflow.core.er_diagram import ERDiagram
from tabulaflow.core.formatters.base import BaseSQLSchemaFormatter
from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.core.schema_compressor import SchemaCompressor
from tabulaflow.core.types import SQLSchema, Usage
from tabulaflow.modulehub.base import CacheableResult, CachedPreprocessorMixin, preprocessor_registry
from tabulaflow.toolhub.run_query import RunQueryTool
from tabulaflow.core.llm import make_agent

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
        agent = make_agent(self.llm, output_type=ERDiagram, instructions=system_prompt, tools=[run_query_tool.as_pydantic_ai_tool()])
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
