"""Transfer-source-table tool backed by a DBRegistry."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic_ai import Tool

from tabulaflow.data.registry import DBRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.output.specs import FixedResultSource

from tabulaflow.output.store import OutputStore, SourceResolutionError


class RegistryTransferSourceTableTool:
    """Persist a fixed output source into a target SQL table.

    This tool resolves a prior ``run_query`` output source and writes that DataFrame into a
    target table. The target can be the session workspace DB or any writable
    SQL connector registered in the runtime.
    """

    name: ClassVar = "transfer_source_table"

    def __init__(
        self,
        registry: DBRegistry,
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
        mode: Literal["append", "replace"] = "append",
    ) -> str:
        """Transfer a fixed source's table into a SQL target table.

        Args:
            source_id: Source ID from ``run_query`` (for example ``S3``).
                To transfer a complete table, first run ``SELECT * FROM <table>``
                without ``LIMIT``, then transfer that source.
            target_alias: Destination database alias.
            target_schema: Optional destination schema name.
            target_table: Destination table name.
            mode: ``append`` to insert rows, ``replace`` to recreate table.
        """
        try:
            source = self._output_store.get_source(source_id)
            if not isinstance(source, FixedResultSource):
                return f"(error: source_id {source_id!r} is not a single-result source)"
            payload = await self._output_store.get_payload(source.result_id)
        except KeyError:
            return f"(error: unknown source_id {source_id!r})"
        except SourceResolutionError as e:
            return f"(error: {e})"

        try:
            df = payload.df
            if df is None:
                return f"(error: source_id {source_id!r} returned no data)"
        except ValueError as e:
            return f"(error: {e})"

        try:
            connector = self.registry.get(target_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(error: unknown target_alias: {target_alias!r}; available: {available})"

        if connector.connector_type != "sql":
            return (
                "(error: transfer_source_table currently supports SQL targets only; "
                f"got connector_type={connector.connector_type!r})"
            )
        if not isinstance(connector, SQLConnector):
            return "(error: unsupported SQL connector implementation for transfer_source_table)"

        try:
            rows_written = await connector.write_dataframe_async(
                df=df,
                table_name=target_table,
                schema_name=target_schema,
                mode=mode,
            )
        except ValueError as e:
            return f"(error: {e})"

        target_name = f"{target_schema}.{target_table}" if target_schema else target_table
        return (
            f"Transferred {rows_written} rows from {source_id} "
            f"({payload.metadata.db_alias}) to alias={target_alias}, table={target_name} (mode={mode})"
        )

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
