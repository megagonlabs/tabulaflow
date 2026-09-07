"""Get-column-json-schema tool backed by a DataConnectorRegistry."""

from typing import ClassVar

from pydantic_ai import Tool, ToolReturn

from tabulaflow.core.schema import SQLSchema
from tabulaflow.data.protocols import DataConnector
from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.agents.tools.protocols import ToolCallOutcome, sum_tool_metrics
from tabulaflow.agents.tools.get_column_json_schema import GetColumnJsonSchemaTool, GetColumnJsonSchemaToolMetrics


class RegistryGetColumnJsonSchemaTool:
    """Retrieve the JSON schema of a column from any registered SQL database.

    The agent specifies which database to target via ``db_alias``.  The tool
    resolves the alias through a ``DataConnectorRegistry`` and delegates to a per-alias
    ``GetColumnJsonSchemaTool`` instance.
    """

    name: ClassVar = "get_column_json_schema"

    def __init__(
        self,
        registry: DataConnectorRegistry,
        *,
        include_examples: bool = True,
        max_example_chars: int = 1000,
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            include_examples: Whether to include example values in the output.
            max_example_chars: Character budget for example values.
        """
        self.registry = registry
        self.include_examples = include_examples
        self.max_example_chars = max_example_chars
        self._tools: dict[str, tuple[DataConnector, SQLSchema, GetColumnJsonSchemaTool]] = {}

    def _get_tool(self, db_alias: str) -> GetColumnJsonSchemaTool:
        """Return a cached ``GetColumnJsonSchemaTool`` for ``db_alias``, rebuilding it if the alias was re-bound."""
        connector = self.registry.get(db_alias)
        entry = self._tools.get(db_alias)
        if entry is not None and entry[0] is connector and entry[1] is connector.schema:
            return entry[2]
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            raise TypeError(
                f"get_column_json_schema is only supported for SQL connectors, not {connector.connector_type!r}"
            )
        tool = GetColumnJsonSchemaTool(
            schema,
            include_examples=self.include_examples,
            max_example_chars=self.max_example_chars,
        )
        self._tools[db_alias] = (connector, schema, tool)
        return tool

    async def __call__(
        self,
        db_alias: str,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        path: str | None = None,
    ) -> ToolReturn:
        """Get the JSON schema of a column, describing its internal structure.

        Useful for semi-structured column types such as VARIANT, OBJECT, ARRAY,
        JSON, and JSONB that store nested or complex data.

        When called without a path, returns a shallow overview of the schema.
        To drill into a specific sub-structure, provide a dot-separated path.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            schema_name: The name of the schema, or None if not applicable.
            table_name: The name of the table.
            column_name: The name of the column.
            path: Optional dot-separated path to a nested sub-schema.
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
            result = await tool.execute(schema_name, table_name, column_name, path)
        except ValueError as e:
            return ToolReturn(return_value=f"(error: {e})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(return_value=result)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetColumnJsonSchemaToolMetrics:
        """Return aggregated metrics across all aliases."""
        return sum_tool_metrics((t.metrics() for _, _, t in self._tools.values()), GetColumnJsonSchemaToolMetrics)
