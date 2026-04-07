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

    def __init__(self, registry: DBRegistry, *, subagent_llm: str = "openai-responses:gpt-5-mini") -> None:
        """Initialize the tool.

        Args:
            registry: Registry containing available connectors.
            subagent_llm: LLM identifier used by per-row subagent runs.
        """
        self.registry = registry
        self.subagent_llm = subagent_llm
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
            tool = RunSubagentForEachRowTool(connector, subagent_llm=self.subagent_llm)
            self._tools[db_alias] = tool
        tool.on_row_complete = self.on_row_complete
        return tool

    async def __call__(
        self,
        db_alias: str,
        table_name: str,
        task_instruction: str,
        input_columns: list[str] | None = None,
        output_columns: list[str] | None = None,
    ) -> str:
        """Use subagents to process each row of a table and write updates back.

        All target output columns must already exist in the table.

        Args:
            db_alias: Alias of the target database table to update.
            table_name: Target table name. Can be qualified (for example schema.table).
            task_instruction: Concise task instructions for processing each row.
                Use clear unambiguous instructions. Mention the output columns, their
                data types and format requirements.
            input_columns: Optional columns to include in row identity/prompt payload.
                If omitted, all table columns are included.
            output_columns: Optional columns the subagent should update.
                If provided, all output columns must already exist in the target table.
        """
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"
        except TypeError as e:
            return f"(error: {e})"
        return await tool(table_name, task_instruction, input_columns, output_columns)

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
