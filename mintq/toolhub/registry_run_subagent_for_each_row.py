"""Run a row-wise subagent over a table in a registry-backed database."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, Literal

from pydantic_ai import Tool

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
        model_settings: dict[str, object] | None = None,
        store_metadata: bool = False,
    ) -> None:
        """Initialize the tool.

        Args:
            registry: Registry containing available connectors.
            subagent_llm: LLM identifier used by per-row subagent runs.
            model_settings: Optional pydantic-ai model settings passed to
                each subagent run (e.g. ``openai_service_tier``).
            store_metadata: If True, write ``_subagent_success``,
                ``_subagent_message``, and ``_subagent_trajectory`` columns
                back to the target table after each row.
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
                    f"run_subagent_for_each_row is only supported for SQL connectors, "
                    f"not {connector.connector_type!r}"
                )
            tool = RunSubagentForEachRowTool(
                connector,
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
        task_instruction: str,
        key_columns: list[str],
        output_columns: list[str] | None = None,
        sql_filter: str | None = None,
        mode: Literal["agentic", "direct"] = "direct",
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
          Two approaches: (a) (preferred) add a foreign-key column to one table and instruct
          the subagent to look up the other table (via ``run_query``) to resolve the
          match, or (b) add a standardized column to both tables and have the
          subagent normalize each side to a canonical form independently. After
          the tool completes, a standard SQL JOIN on the new column(s) produces
          the final result.

        In ``direct`` mode (default), the subagent receives no tools and only
        produces text output; this tool writes the output to the
        ``output_columns`` automatically. Use ``direct`` mode when you need
        to strictly control the subagent's context (e.g. when running inference
        on a dataset). In ``agentic`` mode, each subagent has ``run_query``
        access and writes updates itself.

        Args:
            db_alias: Alias of the target database to update.
            table_name: Target table name. Can be qualified (e.g. schema.table).
            task_instruction: A Jinja2 template rendered per-row as the subagent
                prompt. Use ``{{ column_name }}`` to interpolate column values.
                For JSON columns, use ``{{ (col | fromjson).field }}`` to access
                nested fields. Example: ``"Classify the sentiment of: {{ review_text }}"``.
            key_columns: Columns the subagent uses in the WHERE clause to
                locate each row.
            output_columns: Columns the subagent should update. In ``direct``
                mode, must be exactly one column. If provided, all must
                already exist in the target table.
            sql_filter: A ``SELECT *`` query to select which rows to process.
                Must be a SELECT * query against table_name (e.g.
                ``SELECT * FROM reviews WHERE sentiment IS NULL LIMIT 10``).
                If omitted, all rows are processed.
            mode: Execution mode. ``direct`` (default) gives no tools — the
                subagent produces text output and this tool writes it to
                ``output_columns``. ``agentic`` gives the subagent tools to
                query and update the database.
        """
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"
        except TypeError as e:
            return f"(error: {e})"
        return await tool(
            table_name, task_instruction, key_columns,
            output_columns=output_columns, sql_filter=sql_filter, mode=mode,
        )

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
