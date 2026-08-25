"""Reusable LLM-based database and text summarization."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import jinja2
from pydantic import BaseModel
from pydantic_ai.settings import ModelSettings

from tabulaflow.agents._cache import load_or_compute_model
from tabulaflow.agents.llm import make_agent, make_model_settings
from tabulaflow.agents.runtime import _get_agent_runtime
from tabulaflow.agents.trace import Usage
from tabulaflow.core._cache import stable_cache_key
from tabulaflow.data.protocols import DBConnector
from tabulaflow.output.formatting.cypher import CypherSchemaFormatter
from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter

_DB_SUMMARY_CACHE_VERSION = "v1"
_DB_SUMMARIZATION_PROMPT = """
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
_DB_USER_PROMPT_MAX_CHARS = 400000
_TEXT_SUMMARIZATION_PROMPT = """
You are a technical writer that summarizes the given text concisely.
- Preserve key information and omit unimportant details.
- Target {max_words} words or fewer.
"""


class DBSummary(BaseModel):
    db_summary_markdown: str


def _database_user_prompt(formatted_schema: str) -> str:
    return f"Generate a summary for the following database:\n\n<db_schema>\n{formatted_schema}\n</db_schema>"


def _truncate_database_prompt(user_prompt: str, max_chars: int = _DB_USER_PROMPT_MAX_CHARS) -> str:
    if len(user_prompt) <= max_chars:
        return user_prompt
    note = "\n\n[truncated: schema text exceeded prompt budget]"
    cutoff = max_chars - len(note)
    return note[:max_chars] if cutoff <= 0 else user_prompt[:cutoff] + note


class DBSummarizer:
    """Produce a cached, human-readable database summary."""

    def __init__(
        self,
        llm: str = "openai-responses:gpt-5.4",
        reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] | None = "high",
        max_summary_words: int = 4000,
        model_settings: ModelSettings | None = None,
    ) -> None:
        self.llm = llm
        self.sql_formatter = SQLDDLSchemaFormatter(max_total_columns=200, compact_table_families=True)
        self.graph_formatter = CypherSchemaFormatter()
        self.reasoning_effort = reasoning_effort
        self.max_summary_words = max_summary_words
        self.extra_model_settings = model_settings
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    def _cache_path(self, cache_dir: Path, connector: DBConnector) -> Path:
        key = stable_cache_key(
            {
                "version": _DB_SUMMARY_CACHE_VERSION,
                "global_id": connector.global_id,
                "schema": connector.schema.model_dump(mode="json"),
                "llm": self.llm,
                "reasoning_effort": self.reasoning_effort,
                "max_summary_words": self.max_summary_words,
                "model_settings": self.extra_model_settings,
            }
        )
        return cache_dir / "agent" / "db_summaries" / f"{_DB_SUMMARY_CACHE_VERSION}@{key}.json"

    async def summarize(self, connector: DBConnector) -> DBSummary:
        config = _get_agent_runtime().config
        return await load_or_compute_model(
            path=self._cache_path(config.cache_dir, connector),
            mode=config.preprocessing_cache_mode,
            model_type=DBSummary,
            compute=lambda: self._summarize(connector),
        )

    async def _summarize(self, connector: DBConnector) -> DBSummary:
        from tabulaflow.agents.tools.run_query import RunQueryTool

        system_prompt = jinja2.Template(_DB_SUMMARIZATION_PROMPT).render(max_summary_words=self.max_summary_words)
        if connector.connector_type == "sql":
            sql_schema = connector.schema
            if not sql_schema.tables:
                return DBSummary(db_summary_markdown=f"# Database: `{sql_schema.name}`\n\nThis database has no tables.")
            user_prompt = _database_user_prompt(self.sql_formatter.format(sql_schema, include_descriptions=True))
        elif connector.connector_type == "property_graph":
            graph_schema = connector.schema
            if not graph_schema.nodes and not graph_schema.relationships:
                return DBSummary(
                    db_summary_markdown=f"# Database: `{graph_schema.name}`\n\nThis graph database has no nodes or relationships."
                )
            user_prompt = _database_user_prompt(self.graph_formatter.format(graph_schema))
        else:
            raise TypeError(f"Unsupported connector type for DBSummarizer: {connector.connector_type!r}")

        model_settings: dict[str, Any] = dict(
            make_model_settings(model=self.llm, reasoning_effort=self.reasoning_effort)
        )
        model_settings.update(self.extra_model_settings or {})
        agent = make_agent(
            self.llm,
            output_type=DBSummary,
            instructions=system_prompt,
            tools=[RunQueryTool(connector).as_pydantic_ai_tool()],
            model_settings=model_settings,
        )
        result = await agent.run(_truncate_database_prompt(user_prompt))
        self._usage += Usage.from_pydantic_ai_usage(result.usage, self.llm)
        return result.output


class TextSummarizer:
    """Summarize long text using an LLM."""

    def __init__(
        self,
        llm: str = "openai-responses:gpt-5-mini",
        max_words: int = 500,
        model_settings: ModelSettings | None = None,
    ) -> None:
        self.llm = llm
        self.max_words = max_words
        self.model_settings = model_settings

    async def summarize(self, text: str) -> str:
        settings: dict[str, object] = dict(make_model_settings(model=self.llm, reasoning_effort="low"))
        if self.model_settings:
            settings.update(self.model_settings)
        agent = make_agent(
            self.llm,
            instructions=_TEXT_SUMMARIZATION_PROMPT.format(max_words=self.max_words),
            model_settings=settings,
        )
        result = await agent.run(text)
        return result.output
