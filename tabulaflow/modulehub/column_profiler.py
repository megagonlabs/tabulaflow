import asyncio
import copy
import json
import jinja2
from pydantic import BaseModel
from pydantic_ai.settings import ModelSettings
from tabulaflow.core.types import SQLSchema, ColumnRef, Usage
from tabulaflow.core.db_connector import BaseSQLDBConnector
from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.core.llm import make_agent

COLUMN_PROFILER_SYSTEM_PROMPT = """
<goal>
You are a helpful AI database expert responsible for profiling columns in the database schema.
You will be given the full database schema and a column to profile.
Your goal is to generate descriptions and identify if the column is not used.
</goal>

<tool_calling>
You may call the `run_query` tool multiple times to inspect the data. This is particularly useful for columns with complex or nested structures.
</tool_calling>

<output>
Your output should include:
- `revised_concise_description`: a concise description that begins with a simple noun phrase, adding clarifying details only when necessary.
  - If a column already has a description, revise it to be more concise and informative.
  - Do not repeat information already covered by column metadata (such as data type or categorical values).
  - Retain any non-redundant information from the original description, including notes indicating that a column is not useful.
- optionally `detailed_description_markdown`: only needed for complex columns with nested structures like JSON.
  - a markdown-formatted explanation for complex JSON columns.
  - null for most columns.
- optionally `not_used`:
  - True for columns that contain no valid data or have been explicitly marked as "not useful" in the original description.
  - Do not set this to true if the column is a primary key or is involved in a foreign key.
</output>

<database_schema>
{{schema}}
</database_schema>
""".strip()


def format_user_prompt(column_ref: ColumnRef) -> str:
    return "Generate descriptions for the following column:\n" + json.dumps(column_ref.model_dump(), indent=2)


class LLMOutput(BaseModel):
    revised_concise_description: str
    detailed_description_markdown: str | None = None
    not_used: bool = False


class ColumnProfiler:
    def __init__(self, llm: str = "openai-responses:gpt-5-mini", model_settings: ModelSettings | None = None):
        self.llm = llm
        self.model_settings = model_settings
        self.formatter = SQLDDLSchemaFormatter(max_total_columns=200)
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    async def run_column_async(
        self, db_connector: BaseSQLDBConnector, schema: SQLSchema, column_ref: ColumnRef
    ) -> LLMOutput:
        system_prompt = jinja2.Template(COLUMN_PROFILER_SYSTEM_PROMPT).render(
            schema=self.formatter.format(schema, add_description=True)
        )
        # run_query_tool = RunQueryNoParamsTool(db_connector)
        agent = make_agent(
            self.llm,
            output_type=LLMOutput,
            instructions=system_prompt,
            model_settings=self.model_settings,
        )
        user_prompt = format_user_prompt(column_ref)
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage, self.llm)
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
            column.not_used = result.not_used
        return new_schema
