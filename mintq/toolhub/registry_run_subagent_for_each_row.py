"""Run a row-wise subagent over a table in a registry-backed database."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

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
    ) -> None:
        """Initialize the tool.

        Args:
            registry: Registry containing available connectors.
            subagent_llm: LLM identifier used by per-row subagent runs.
            model_settings: Optional pydantic-ai model settings passed to
                each subagent run (e.g. ``openai_service_tier``).
        """
        self.registry = registry
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
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
            tool = RunSubagentForEachRowTool(connector, subagent_llm=self.subagent_llm, model_settings=self.model_settings)
            self._tools[db_alias] = tool
        tool.on_row_complete = self.on_row_complete
        return tool

    async def __call__(
        self,
        db_alias: str,
        table_name: str,
        task_instruction: str,
        key_columns: list[str],
        input_columns: list[str] | None = None,
        output_columns: list[str] | None = None,
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

        Each subagent has ``run_query`` access, so it can look up other tables as
        needed for join resolution. All target output columns must already exist in
        the table.

        Args:
            db_alias: Alias of the target database to update.
            table_name: Target table name. Can be qualified (e.g. schema.table).
            task_instruction: Concise task instructions for processing each row.
                Use clear, unambiguous instructions. Mention the output columns,
                their data types, and format requirements.
            key_columns: Columns the subagent uses in the WHERE clause to
                locate each row.
            input_columns: Columns to include in the row payload sent to the
                subagent as context. If omitted, all table columns are included.
            output_columns: Columns the subagent should update. If provided, all
                must already exist in the target table.
        """
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"
        except TypeError as e:
            return f"(error: {e})"
        return await tool(table_name, task_instruction, key_columns, input_columns, output_columns)

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
