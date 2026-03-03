from typing import ClassVar, Literal
from pydantic import BaseModel, Field
import jinja2
from pydantic_ai import Agent
from mintq.formatters.base import BaseSQLSchemaFormatter
from mintq.preprocessors.components.schema_compressor import SchemaCompressor
from mintq.schema import SQLSchema, TableRef, Usage
from mintq.db_connector import BaseSQLDBConnector
from mintq.preprocessors.base import CachedPreprocessorMixin, preprocessor_registry, CacheableResult
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
from mintq.toolhub.run_query import RunQueryNoParamsTool

SUMMARIZATION_PROMPT = """
You are an AI database expert tasked with producing a summary for a database.

<requirements>
- The summary should be in markdown format, under 2000 words.
- Your output should contain only the summary without further suggestions or explanations.
- Keep the content clear, precise, and concise.
- Describe the core entities and the relationships within the database.
- Ensure all table names are mentioned so that a reader can identify all tables in the database from the summary.
- For important relationships, provide the corresponding join paths illustrated with a SQL snippet.
</requirements>
""".strip()


def format_user_prompt(schema: SQLSchema, formatter: BaseSQLSchemaFormatter) -> str:
    return "Generate a summary for the following database:\n" + formatter.format(schema, add_description=True)


class DBSummary(BaseModel):
    db_summary_markdown: str


@preprocessor_registry.register
class DBSummarizer(CachedPreprocessorMixin[DBSummary]):
    name: ClassVar[str] = "db_summarizer"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"
    output_type: ClassVar[type[CacheableResult]] = DBSummary

    def __init__(self, llm: str = "openai-responses:gpt-5-mini", compress_schema: bool = True):
        self.llm = llm
        self.compressor = SchemaCompressor() if compress_schema else None
        self.formatter = SQLDDLSchemaFormatter()
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    def _get_cache_id_suffix(self) -> str:
        return "_" + self.llm.replace(":", "--")

    async def _preprocess_impl_async(self, db_connector: BaseSQLDBConnector) -> DBSummary:
        schema = db_connector.schema
        if self.compressor is not None:
            schema = self.compressor.compress(schema)

        system_prompt = jinja2.Template(SUMMARIZATION_PROMPT).render()
        run_query_tool = RunQueryNoParamsTool(db_connector)
        agent = Agent[None, DBSummary](
            model=self.llm,
            output_type=DBSummary,
            instructions=system_prompt,
            tools=[run_query_tool.as_pydantic_ai_tool()],
        )
        user_prompt = format_user_prompt(schema, self.formatter)
        result = await agent.run(user_prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        return result.output
