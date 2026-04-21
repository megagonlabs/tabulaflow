"""Transfer-record tool backed by a DBRegistry."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic_ai import Tool

from mintq.db_connector.db_registry import DBRegistry
from mintq.db_connector.sql_conn import SQLConnector

from mintq.toolhub.registry_run_query import QueryHistory


class RegistryTransferRecordTool:
    """Persist a query-history record into a target SQL table.

    This tool is intentionally record-centric: callers reference a prior
    ``run_query`` output by ``record_id`` and write that DataFrame into a
    target table. The target can be the session workspace DB or any writable
    SQL connector registered in the runtime.
    """

    name: ClassVar = "transfer_record"

    def __init__(
        self,
        registry: DBRegistry,
        history: QueryHistory,
    ) -> None:
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            history: Shared query-history store used by ``run_query``.
        """
        self.registry = registry
        self._history = history

    async def __call__(
        self,
        record_id: str,
        target_alias: str,
        target_schema: str | None,
        target_table: str,
        mode: Literal["append", "replace"] = "append",
    ) -> str:
        """Transfer a stored query result into a SQL target table.

        Args:
            record_id: Query record ID from ``run_query`` (for example ``Q3``).
            target_alias: Destination database alias.
            target_schema: Optional destination schema name.
            target_table: Destination table name.
            mode: ``append`` to insert rows, ``replace`` to recreate table.
        """
        try:
            record = await self._history.get(record_id)
        except KeyError:
            return f"(error: unknown record_id {record_id!r})"

        pred = record.pred_query
        if pred.exec_result is None or pred.exec_result.df is None:
            return f"(error: query {record.record_id} returned no data)"

        try:
            connector = self.registry.get(target_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown target_alias: {target_alias!r}; available: {available})"

        if connector.connector_type != "sql":
            return (
                "(error: transfer_record currently supports SQL targets only; "
                f"got connector_type={connector.connector_type!r})"
            )
        if not isinstance(connector, SQLConnector):
            return "(error: unsupported SQL connector implementation for transfer_record)"

        df = pred.exec_result.df
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
            f"Transferred {rows_written} rows from {record.record_id} "
            f"({record.db_alias}) to alias={target_alias}, table={target_name} (mode={mode})"
        )

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
