import asyncio
import copy
import json
from typing import ClassVar
import jinja2
from pydantic import BaseModel
from pydantic_ai import Agent
from mintq.schema import SQLSchema, ColumnRef, Usage
from mintq.db_connector import BaseSQLDBConnector
from mintq.toolhub.run_query import RunQueryNoParamsTool
from mintq.formatters.sql_default import SQLDefaultSchemaFormatter

COLUMN_PROFILER_SYSTEM_PROMPT = """
You are a helpful AI database expert responsible for generating column descriptions for database schema fields.

- If a column already has a description, revise it to be more concise and informative.
- Do not repeat information already covered by column metadata (such as data type or categorical values).
- Retain any non-redundant information from the original description, including notes indicating that a column is not useful.
- For columns with complex or nested structures, you may use the `run_query` tool multiple times to inspect the data.
- The concise description should begin with a noun phrase, adding brief clarifying details only if needed.
- The detailed description should be:
  - null for simple columns where the concise description is sufficient
  - a markdown-formatted explanation for complex columns

=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===
""".strip()


def format_user_prompt(column_ref: ColumnRef) -> str:
    return "Generate descriptions for the following column:\n" + json.dumps(column_ref.model_dump(), indent=2)


class LLMOutput(BaseModel):
    revised_concise_description: str
    detailed_description_markdown: str | None


class ColumnProfiler:
    name: ClassVar[str] = "column_profiler"

    def __init__(self, llm: str = "openai-responses:gpt-5-mini"):
        self.llm = llm
        self.formatter = SQLDefaultSchemaFormatter()
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    async def run_column_async(
        self, db_connector: BaseSQLDBConnector, schema: SQLSchema, column_ref: ColumnRef
    ) -> LLMOutput:
        system_prompt = jinja2.Template(COLUMN_PROFILER_SYSTEM_PROMPT).render(
            schema=self.formatter.format(schema, add_description=True)
        )
        run_query_tool = RunQueryNoParamsTool(db_connector)
        agent = Agent[None, LLMOutput](
            model=self.llm,
            output_type=LLMOutput,
            instructions=system_prompt,
            tools=[run_query_tool.as_pydantic_ai_tool()],
        )
        user_prompt = format_user_prompt(column_ref)
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        return result.output

    async def run_async(self, db_connector: BaseSQLDBConnector, schema: SQLSchema) -> SQLSchema:
        column_refs = schema.get_all_column_refs()
        all_results = await asyncio.gather(
            *[self.run_column_async(db_connector, schema, column_ref) for column_ref in column_refs]
        )
        new_schema = copy.deepcopy(schema)
        for column_ref, result in zip(column_refs, all_results):
            column = new_schema.get_column_by_ref(column_ref)
            column.description = result.revised_concise_description
            column.detailed_description_markdown = result.detailed_description_markdown
        return new_schema
