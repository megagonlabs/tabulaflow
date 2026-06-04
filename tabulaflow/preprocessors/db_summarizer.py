import jinja2
from pydantic import BaseModel
from pydantic_ai import Agent

from typing import Any, ClassVar, Literal

from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.core.formatters.cypher import CypherSchemaFormatter
from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.preprocessors.base import CachedPreprocessorMixin, CacheableResult, preprocessor_registry
from tabulaflow.preprocessors.components.schema_compressor import SchemaCompressor
from tabulaflow.core.types import Usage

SUMMARIZATION_PROMPT = """
You are an AI database expert tasked with producing a summary for a database.
The purpose of the summary is to help database experts explore the database and write database queries efficiently and accurately.

<requirements>
- The summary should be in markdown format.
- The summary should be up to {{ max_summary_words }} words. Use fewer words for simple databases and more words only when complexity justifies it.
- The title should be in the format "Database: `<database_name>`".
- Your output should contain only the summary without further suggestions or explanations. Do not append "end of summary" at the end.
- Keep the content clear, precise, and concise.
- Describe the core entities and the relationships within the database.
- For SQL databases: when referring to tables, use schema-qualified table names (e.g. `schema.table`) if a schema is present.
</requirements>
""".strip()

_USER_PROMPT_MAX_CHARS = 400000


def format_user_prompt(formatted_schema: str) -> str:
    return f"Generate a summary for the following database:\n\n<db_schema>\n{formatted_schema}\n</db_schema>"


def truncate_user_prompt(user_prompt: str, max_chars: int = _USER_PROMPT_MAX_CHARS) -> str:
    """Truncate user prompt to avoid exceeding model context limits."""
    if len(user_prompt) <= max_chars:
        return user_prompt
    note = "\n\n[truncated: schema text exceeded prompt budget]"
    cutoff = max_chars - len(note)
    if cutoff <= 0:
        return note[:max_chars]
    return user_prompt[:cutoff] + note


class DBSummary(BaseModel):
    db_summary_markdown: str


@preprocessor_registry.register
class DBSummarizer(CachedPreprocessorMixin[DBSummary]):
    name: ClassVar[str] = "db_summarizer"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"
    output_type: ClassVar[type[CacheableResult]] = DBSummary

    def __init__(
        self,
        llm: str = "openai-responses:gpt-5.4",
        compress_schema: bool = True,
        openai_reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] | None = "high",
        max_summary_words: int = 4000,
        model_settings: dict[str, object] | None = None,
    ) -> None:
        self.llm = llm
        self.compressor = SchemaCompressor() if compress_schema else None
        self.sql_formatter = SQLDDLSchemaFormatter(max_total_columns=200)
        self.graph_formatter = CypherSchemaFormatter()
        self.openai_reasoning_effort = openai_reasoning_effort
        self.max_summary_words = max_summary_words
        self.extra_model_settings = model_settings
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    def _get_cache_id_suffix(self) -> str:
        return "_" + self.llm.replace(":", "--")

    async def _preprocess_impl_async(self, db_connector: NL2QDBConnector) -> DBSummary:
        from tabulaflow.core.tools.run_query import RunQueryTool

        system_prompt = jinja2.Template(SUMMARIZATION_PROMPT).render(max_summary_words=self.max_summary_words)

        if db_connector.connector_type == "sql":
            schema = db_connector.schema
            if not schema.tables:
                return DBSummary(db_summary_markdown=f"# Database: `{schema.name}`\n\nThis database has no tables.")
            if self.compressor is not None:
                schema = self.compressor.compress(schema)
            user_prompt = format_user_prompt(self.sql_formatter.format(schema, add_description=True))
        elif db_connector.connector_type == "property_graph":
            graph_schema = db_connector.schema
            if not graph_schema.nodes and not graph_schema.relationships:
                return DBSummary(
                    db_summary_markdown=f"# Database: `{graph_schema.name}`\n\nThis graph database has no nodes or relationships."
                )
            user_prompt = format_user_prompt(self.graph_formatter.format(graph_schema))
        else:
            raise TypeError(f"Unsupported connector type for DBSummarizer: {db_connector.connector_type!r}")

        run_query_tool = RunQueryTool(db_connector)

        model_settings: dict[str, Any] = dict(self.extra_model_settings or {})
        if self.openai_reasoning_effort is not None:
            model_settings["openai_reasoning_effort"] = self.openai_reasoning_effort
            model_settings["openai_reasoning_summary"] = "detailed"

        agent = Agent[None, DBSummary](  # type: ignore
            model=self.llm,
            output_type=DBSummary,
            instructions=system_prompt,
            tools=[run_query_tool.as_pydantic_ai_tool()],
            model_settings=model_settings,
        )
        result = await agent.run(truncate_user_prompt(user_prompt))
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        return result.output  # type: ignore
