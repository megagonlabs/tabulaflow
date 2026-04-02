"""Get-table-schema tool backed by a DBRegistry."""

from typing import ClassVar

from pydantic_ai import Tool

from mintq.db_connector.base import BaseSQLDBConnector
from mintq.db_connector.db_registry import DBRegistry
from mintq.formatters.base import BaseSQLSchemaFormatter
from mintq.toolhub.get_table_schema import GetTableSchemaTool, GetTableSchemaToolMetrics


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
        formatter: BaseSQLSchemaFormatter,
        *,
        compress: bool = True,
        add_description: bool = True,
        max_columns: int | None = 50,
        enable_refresh: bool = False,
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            formatter: The formatter used to render table schema as text.
            compress: Whether to compress the schema.
            add_description: Whether to include column descriptions in output.
            max_columns: If set, reject requests whose resulting columns
                exceed this limit.
            enable_refresh: If True, expose the ``refresh`` parameter to the
                LLM.
        """
        self.registry = registry
        self.formatter = formatter
        self.compress = compress
        self.add_description = add_description
        self.max_columns = max_columns
        self.enable_refresh = enable_refresh
        self._tools: dict[str, GetTableSchemaTool] = {}

    def _get_tool(self, db_alias: str) -> GetTableSchemaTool:
        """Return a cached ``GetTableSchemaTool`` for ``db_alias``, creating one if needed."""
        tool = self._tools.get(db_alias)
        if tool is not None:
            return tool
        connector = self.registry.get(db_alias)
        if not isinstance(connector, BaseSQLDBConnector):
            raise TypeError(f"get_table_schema is only supported for SQL connectors, not {type(connector).__name__}")
        tool = GetTableSchemaTool(
            connector,
            self.formatter,
            compress=self.compress,
            add_description=self.add_description,
            max_columns=self.max_columns,
            enable_refresh=self.enable_refresh,
        )
        self._tools[db_alias] = tool
        return tool

    async def _with_refresh(
        self,
        db_alias: str,
        schema_name: str | None,
        table_name: str,
        refresh: bool = False,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        """Get the full schema of a table, with optional column filtering and pagination.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            schema_name: The name of the schema to which the table belongs,
                or None if schema is not applicable.
            table_name: The name of the table.
            refresh: If True, re-introspect this table from the live database
                before returning.
            column_offset: Number of columns to skip from the beginning.
            column_limit: Maximum number of columns to return.
            column_regex_filter: Regex pattern to filter columns by name
                (case-insensitive).
        """
        return await self._execute(
            db_alias, schema_name, table_name, refresh, column_regex_filter, column_offset, column_limit
        )

    async def _no_refresh(
        self,
        db_alias: str,
        schema_name: str | None,
        table_name: str,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        """Get the full schema of a table, with optional column filtering and pagination.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            schema_name: The name of the schema to which the table belongs,
                or None if schema is not applicable.
            table_name: The name of the table.
            column_offset: Number of columns to skip from the beginning.
            column_limit: Maximum number of columns to return.
            column_regex_filter: Regex pattern to filter columns by name
                (case-insensitive).
        """
        return await self._execute(
            db_alias, schema_name, table_name, False, column_regex_filter, column_offset, column_limit
        )

    async def _execute(
        self,
        db_alias: str,
        schema_name: str | None,
        table_name: str,
        refresh: bool,
        column_regex_filter: str | None,
        column_offset: int,
        column_limit: int | None,
    ) -> str:
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"
        except TypeError as e:
            return f"(error: {e})"
        return await tool(schema_name, table_name, refresh, column_offset, column_limit, column_regex_filter)

    async def __call__(
        self,
        db_alias: str,
        schema_name: str | None,
        table_name: str,
        refresh: bool = False,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        return await self._execute(
            db_alias,
            schema_name,
            table_name,
            refresh if self.enable_refresh else False,
            column_regex_filter,
            column_offset,
            column_limit,
        )

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._with_refresh if self.enable_refresh else self._no_refresh
        return Tool(fn, name=self.name)

    def metrics(self) -> dict[str, GetTableSchemaToolMetrics]:
        """Return per-alias metrics."""
        return {alias: tool.metrics() for alias, tool in self._tools.items()}
