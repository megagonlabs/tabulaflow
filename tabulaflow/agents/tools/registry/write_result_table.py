"""Write-result-table tool backed by a DataConnectorRegistry."""

from __future__ import annotations

from typing import ClassVar

from pydantic_ai import Tool, ToolReturn

from tabulaflow.agents.tools.protocols import ToolCallOutcome
from tabulaflow.data.protocols import DataFrameWriteMode
from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.output.specs import FixedResultSource
from tabulaflow.output.store import OutputStore, SourceResolutionError


class WriteResultTableTool:
    """Write a fixed query result into a target SQL table.

    This tool resolves a prior ``run_query`` result and writes its DataFrame into
    the session workspace or another writable registered SQL database.
    """

    name: ClassVar = "write_result_table"

    def __init__(
        self,
        registry: DataConnectorRegistry,
        output_store: OutputStore,
    ) -> None:
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            output_store: Shared output store used by ``run_query``.
        """
        self.registry = registry
        self._output_store = output_store

    async def __call__(
        self,
        source_id: str,
        target_alias: str,
        target_schema: str | None,
        target_table: str,
        mode: DataFrameWriteMode = "create",
    ) -> ToolReturn:
        """Write a fixed ``run_query`` result into a SQL target table.

        Args:
            source_id: Source ID from ``run_query`` (for example ``S3``).
                To write a complete table, first run ``SELECT * FROM <table>``
                without ``LIMIT``, then write that result.
            target_alias: Destination database alias.
            target_schema: Optional destination schema name.
            target_table: Destination table name.
            mode: ``create`` to create a new table, ``append`` to add rows,
                ``replace_rows`` to replace rows while preserving the table
                definition, or ``replace_table`` to recreate the table.
        """
        try:
            result = await self.execute(source_id, target_alias, target_schema, target_table, mode)
        except (ValueError, TypeError, RuntimeError) as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(return_value=result)

    async def execute(
        self,
        source_id: str,
        target_alias: str,
        target_schema: str | None,
        target_table: str,
        mode: DataFrameWriteMode = "create",
    ) -> str:
        """Write one fixed query result into a registered SQL target."""
        try:
            source = self._output_store.get_source(source_id)
            if not isinstance(source, FixedResultSource):
                raise ValueError(f"source_id {source_id!r} is not a single-result source")
            payload = await self._output_store.get_payload(source.result_id)
        except KeyError:
            raise ValueError(f"unknown source_id {source_id!r}") from None
        except SourceResolutionError as e:
            raise RuntimeError(str(e)) from e

        df = payload.df
        if df is None:
            raise ValueError(f"source_id {source_id!r} returned no data")

        try:
            connector = self.registry.get(target_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown target_alias: {target_alias!r}; available: {available}") from None

        if not isinstance(connector, SQLConnector):
            raise TypeError(
                f"write_result_table supports SQL targets only; got connector_type={connector.connector_type!r}"
            )

        rows_written = await connector.write_dataframe_async(
            df=df,
            table_name=target_table,
            schema_name=target_schema,
            mode=mode,
        )

        target_name = f"{target_schema}.{target_table}" if target_schema else target_table
        return (
            f"Wrote {rows_written} rows from {source_id} "
            f"({payload.metadata.db_alias}) to alias={target_alias}, table={target_name} (mode={mode})"
        )

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
