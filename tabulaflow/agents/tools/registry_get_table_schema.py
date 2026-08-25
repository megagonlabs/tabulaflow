"""Get-table-schema tool backed by a DBRegistry."""

from typing import ClassVar

from pydantic_ai import Tool, ToolReturn

from tabulaflow.data.protocols import DBConnector
from tabulaflow.data.registry import DBRegistry
from tabulaflow.output.formatting.schema import SQLSchemaFormatter
from tabulaflow.agents.tools.base import ToolCallOutcome, _omit_tool_parameters, sum_tool_metrics
from tabulaflow.agents.tools.get_table_schema import GetTableSchemaTool, GetTableSchemaToolMetrics


class RegistryGetTableSchemaTool:
    """Retrieve the schema of a table from any registered SQL database.

    The agent specifies which database to target via ``db_alias``.  The tool
    resolves the alias through a ``DBRegistry`` and delegates to a per-alias
    ``GetTableSchemaTool`` instance.
    """

    name: ClassVar = "get_table_schema"

    def __init__(
        self,
        registry: DBRegistry,
        formatter: SQLSchemaFormatter,
        *,
        include_descriptions: bool = True,
        max_columns: int | None = 50,
        enable_refresh: bool = False,
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            formatter: The formatter used to render table schema as text.
            include_descriptions: Whether to include column descriptions in output.
            max_columns: If set, reject requests whose resulting columns
                exceed this limit.
            enable_refresh: If True, expose the ``refresh`` parameter to the
                LLM.
        """
        self.registry = registry
        self.formatter = formatter
        self.include_descriptions = include_descriptions
        self.max_columns = max_columns
        self.enable_refresh = enable_refresh
        self._tools: dict[str, tuple[DBConnector, GetTableSchemaTool]] = {}

    def _get_tool(self, db_alias: str) -> GetTableSchemaTool:
        """Return a cached ``GetTableSchemaTool`` for ``db_alias``, rebuilding it if the alias was re-bound."""
        connector = self.registry.get(db_alias)
        entry = self._tools.get(db_alias)
        if entry is not None and entry[0] is connector:
            return entry[1]
        if connector.connector_type != "sql":
            raise TypeError(f"get_table_schema is only supported for SQL connectors, not {connector.connector_type!r}")
        tool = GetTableSchemaTool(
            connector,
            self.formatter,
            include_descriptions=self.include_descriptions,
            max_columns=self.max_columns,
            enable_refresh=self.enable_refresh,
        )
        self._tools[db_alias] = (connector, tool)
        return tool

    async def __call__(
        self,
        db_alias: str,
        schema_name: str | None,
        table_name: str,
        refresh: bool = False,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> ToolReturn:
        """Get a table schema from a registered database.

        Args:
            db_alias: Alias of the target database.
            schema_name: Schema containing the table, or ``None`` when schemas
                are not applicable.
            table_name: Name of the table.
            refresh: Whether to re-introspect the table before returning. Exposed
                only when schema refresh is enabled.
            column_offset: Number of columns to skip.
            column_limit: Maximum number of columns to return.
            column_regex_filter: Case-insensitive regex used to select columns.
        """
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return ToolReturn(
                return_value=f"(error: unknown db_alias: {db_alias!r}; available: {available})",
                metadata=ToolCallOutcome(error=True),
            )
        except TypeError as e:
            return ToolReturn(return_value=f"(error: {e})", metadata=ToolCallOutcome(error=True))
        try:
            execution = await tool.execute(
                schema_name,
                table_name,
                refresh=refresh if self.enable_refresh else False,
                column_regex_filter=column_regex_filter,
                column_offset=column_offset,
                column_limit=column_limit,
            )
        except (ValueError, RuntimeError) as e:
            return ToolReturn(return_value=f"(error: {e})", metadata=ToolCallOutcome(error=True))
        outcome = (
            ToolCallOutcome(count=execution.n_columns, unit="columns") if execution.n_columns is not None else None
        )
        return ToolReturn(return_value=execution.output, metadata=outcome)

    def as_pydantic_ai_tool(self) -> Tool:
        omitted = () if self.enable_refresh else ("refresh",)
        return Tool(self.__call__, name=self.name, prepare=_omit_tool_parameters(*omitted))

    def metrics(self) -> GetTableSchemaToolMetrics:
        """Return aggregated metrics across all aliases."""
        return sum_tool_metrics((t.metrics() for _, t in self._tools.values()), GetTableSchemaToolMetrics)
