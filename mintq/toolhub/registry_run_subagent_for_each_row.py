"""Run a row-wise subagent over a table in a registry-backed database."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from pydantic_ai import Tool
from pydantic_ai.settings import ModelSettings

from mintq.db_connector.db_registry import DBRegistry
from mintq.toolhub.run_subagent_for_each_row import RunSubagentForEachRowTool


class RegistryRunSubagentForEachRowTool:
    """Run an LLM subagent for each row of a table and let it write updates.

    The agent specifies which database to target via ``db_alias``. The tool
    resolves the alias through a ``DBRegistry`` and delegates to a per-alias
    ``RunSubagentForEachRowTool`` instance.
    """

    name: ClassVar[str] = "run_subagent_for_each_row"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        store_metadata: bool = False,
    ) -> None:
        """Initialize the tool.

        Args:
            registry: Registry containing available connectors.
            subagent_llm: LLM identifier used by per-row subagent runs.
            model_settings: Optional pydantic-ai model settings passed to
                each subagent run (e.g. ``openai_service_tier``).
            store_metadata: If True, write ``_subagent_exception`` and
                ``_subagent_trajectory`` columns back to the target table
                after each row. ``_subagent_exception`` is NULL on success
                and a ``"<ExceptionType>: <message>"`` string on failure.
        """
        self.registry = registry
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.store_metadata = store_metadata
        self.on_row_complete: Callable[[int, int], None] | None = None
        self._tools: dict[str, RunSubagentForEachRowTool] = {}

    def _get_tool(self, db_alias: str) -> RunSubagentForEachRowTool:
        """Return a cached ``RunSubagentForEachRowTool`` for ``db_alias``, creating one if needed."""
        tool = self._tools.get(db_alias)
        if tool is None:
            connector = self.registry.get(db_alias)
            if connector.connector_type != "sql":
                raise TypeError(
                    f"run_subagent_for_each_row is only supported for SQL connectors, not {connector.connector_type!r}"
                )
            tool = RunSubagentForEachRowTool(
                connector,
                registry=self.registry,
                subagent_llm=self.subagent_llm,
                model_settings=self.model_settings,
                store_metadata=self.store_metadata,
            )
            self._tools[db_alias] = tool
        tool.on_row_complete = self.on_row_complete
        return tool

    async def __call__(
        self,
        db_alias: str,
        table_name: str,
        *,
        task_query: str,
        task_instruction: str,
        key_columns: list[str],
        output_columns: list[str],
        enable_browser_tools: bool = False,
        enable_nested_subagents: bool = False,
        enable_run_query_tool: bool = False,
    ) -> str:
        """Run an LLM subagent on each row to perform operations beyond standard SQL.

        This is the execution primitive for semantic operators — tasks where the
        predicate, join condition, or transformation requires natural-language
        understanding rather than exact SQL expressions. Prefer this tool over
        fuzzy regex matching or LIKE-based SQL for these tasks. Common patterns:

        - **Semantic filter**: Classify a free-text column against a natural-language
          predicate (e.g., "is this review positive or negative?").
        - **Semantic extraction**: Extract structured values from unstructured text
          (e.g., extract sentiment, topic, or named entities from a comment).
        - **Semantic join**: Match rows across tables where there is no shared key
          and no syntactic overlap between join columns (e.g., abbreviations to
          full names, or matching product names across different naming conventions).
          Two approaches:
          (a) (preferred when the lookup space is large) Add a foreign-key column
              to one table and have the subagent resolve the match against the
              other table at runtime via ``run_query`` — set
              ``enable_run_query_tool=True``. Avoid embedding a large vocabulary
              in the task instruction.
          (b) Add a standardized column to both tables and have the subagent
              normalize each side to a canonical form (e.g., IATA airport code)
              independently. No ``run_query`` access needed.
          After the tool completes, a standard SQL JOIN on the new column(s)
          produces the final result.

        The per-row subagent receives no database tools by default and produces a
        single text value; this tool writes that value to ``output_columns[0]``.
        Set ``enable_browser_tools=True`` to grant web-browsing tools, or
        ``enable_run_query_tool=True`` to grant a read-only ``run_query`` tool
        that can target any registered database.

        Args:
            db_alias: Alias of the target database to update.
            table_name: Target table name. Can be qualified (e.g. schema.table).
                Used as the write-back target; per-row updates locate rows here
                via ``key_columns``.
            task_query: SELECT query producing one row per subagent task. Free-form:
                may join tables, compute new columns, etc. The result columns
                become the variables available to ``task_instruction``. Must
                include all ``key_columns``. Pass ``SELECT * FROM <table_name>``
                as a default.
            task_instruction: A Jinja2 template rendered per-row as the subagent
                prompt. Use ``{{ column_name }}`` to interpolate values from the
                ``task_query`` result; standard Jinja control flow
                (``{% for %}``, ``{% if %}``) is available. For JSON columns,
                extract the field or cast to an array in ``task_query`` using
                the dialect's JSON functions rather than relying on the
                template — driver materialization varies (string vs structure)
                and only structured projections iterate reliably. Example:
                ``"Classify the sentiment of: {{ review_text }}"``.
            key_columns: Columns used in the WHERE clause to locate each row in
                ``table_name`` for write-back. Must appear in the ``task_query``
                result.
            output_columns: Columns to update on ``table_name``. Must be exactly
                one column; it must already exist on the target table (does not
                need to appear in the ``task_query`` projection).
            enable_browser_tools: If True, the per-row subagent additionally
                receives web-browsing tools (navigate, click, type, scroll,
                etc.). Use for tasks that require fetching information from the
                web.
            enable_nested_subagents: If True, each per-row subagent additionally
                receives this ``run_subagent_for_each_row`` tool, allowing it
                to fan out further row-wise tasks of its own. The flag does not
                propagate automatically — each nested level must opt in
                explicitly.
            enable_run_query_tool: If True, the per-row subagent additionally
                receives a registry-backed ``run_query`` tool that can target
                any registered database (the subagent specifies ``db_alias``
                per call). Use for runtime lookups across tables — including
                in databases other than the one being updated. The subagent
                still produces text output and does not write its own
                updates — write-back remains this tool's responsibility.
        """
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"
        except TypeError as e:
            return f"(error: {e})"
        return await tool(
            table_name,
            task_query=task_query,
            task_instruction=task_instruction,
            key_columns=key_columns,
            output_columns=output_columns,
            enable_browser_tools=enable_browser_tools,
            enable_nested_subagents=enable_nested_subagents,
            enable_run_query_tool=enable_run_query_tool,
        )

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
