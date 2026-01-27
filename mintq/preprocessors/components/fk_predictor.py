import asyncio
import copy
import json
from typing import ClassVar
import jinja2
from pydantic import BaseModel
from pydantic_ai import Agent
from mintq.schema import SQLSchema, Usage, ForeignKeySchema, TableRef
from mintq.db_connector import BaseSQLDBConnector
from mintq.toolhub.run_query import RunQueryNoParamsTool
from mintq.formatters.sql_basic import SQLBasicSchemaFormatter

FK_PREDICTOR_SYSTEM_PROMPT = """

You are an AI database expert tasked with discovering and documenting missing foreign key constraints for a specific database table.

- Identify all missing outgoing foreign key relationships defined from this table to other tables.
- For each foreign key, populate the `columns` field as follows:
  - Use a list containing a single column name for single-column foreign keys.
  - Use a list containing all participating column names for composite foreign keys.
- You may use the `run_query` tool to inspect data and verify potential foreign key relationships.

=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===
""".strip()


def format_user_prompt(table_ref: TableRef) -> str:
    res = "Identify missing outgoing foreign keys from the following table:"
    res += "\n" + json.dumps(table_ref.model_dump(), indent=2)
    return res


class LLMOutput(BaseModel):
    missing_foreign_keys: list[ForeignKeySchema]


class ForeignKeyPredictor:
    def __init__(self, llm: str = "openai-responses:gpt-5-mini"):
        self.llm = llm
        self.formatter = SQLBasicSchemaFormatter()
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    async def run_table_async(
        self, db_connector: BaseSQLDBConnector, schema: SQLSchema, table_ref: TableRef
    ) -> list[ForeignKeySchema]:
        system_prompt = jinja2.Template(FK_PREDICTOR_SYSTEM_PROMPT).render(
            schema=self.formatter.format(schema, add_description=True)
        )
        run_query_tool = RunQueryNoParamsTool(db_connector)
        agent = Agent[None, LLMOutput](
            model=self.llm,
            output_type=LLMOutput,
            instructions=system_prompt,
            tools=[run_query_tool.as_pydantic_ai_tool()],
        )
        user_prompt = format_user_prompt(table_ref)
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        return result.output.missing_foreign_keys

    async def run_async(self, db_connector: BaseSQLDBConnector, schema: SQLSchema) -> SQLSchema:
        table_refs = schema.get_all_table_refs()
        all_results = await asyncio.gather(
            *[self.run_table_async(db_connector, schema, table_ref) for table_ref in table_refs]
        )

        new_schema = copy.deepcopy(schema)

        def hash_fk(fk: ForeignKeySchema) -> str:
            return (
                tuple(sorted(fk.columns)),
                fk.foreign_schema_name,
                fk.foreign_table,
                tuple(sorted(fk.foreign_columns)),
            )

        for table_ref, fks in zip(table_refs, all_results):
            table = new_schema.get_table_by_ref(table_ref)
            for fk in fks:
                if any(hash_fk(fk) == hash_fk(existing_fk) for existing_fk in table.foreign_keys):
                    continue
                table.foreign_keys.append(fk)
                for col in table.columns:
                    if col.name in fk.columns:
                        col.foreign_keys.append(fk)
        return new_schema
