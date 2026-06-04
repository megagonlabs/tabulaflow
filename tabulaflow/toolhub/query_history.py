"""Session-level query history with LRU spill to a workspace DuckDB."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from tabulaflow.core.types import PredQuery

if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.core.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

_QH_SCHEMA = "_query_history"


@dataclass
class QueryRecord:
    """Metadata for a query executed through the registry tool."""

    record_id: str
    connector_type: Literal["sql", "property_graph"]
    db_alias: str
    pred_query: PredQuery
    vegalite_spec: dict[str, Any] | None = None


class QueryHistory:
    """Query history with write-through spill to a workspace DuckDB.

    Every successful result DataFrame is persisted to the workspace
    connector (when set).  The most recent ``max_in_memory`` DFs are also
    kept in RAM; older ones are evicted and transparently reloaded from the
    workspace on access via ``get()``.

    Args:
        max_in_memory: Number of result DataFrames to keep in RAM.
    """

    def __init__(
        self,
        *,
        max_in_memory: int = 5,
        spill_connector: SQLConnector | None = None,
    ) -> None:
        if max_in_memory < 1:
            raise ValueError("max_in_memory must be >= 1")
        self._records: dict[str, QueryRecord] = {}
        self._next_query_id = 1
        self._max_in_memory = max_in_memory
        self._in_memory: deque[str] = deque()
        self._spilled: set[str] = set()
        self._spill_connector = spill_connector
        self._schema_created = False

    async def add(
        self, db_alias: str, connector_type: Literal["sql", "property_graph"], pred_query: PredQuery
    ) -> QueryRecord:
        """Store a query and assign it the next opaque record ID."""
        record_id = f"Q{self._next_query_id}"
        record = QueryRecord(
            record_id=record_id, connector_type=connector_type, db_alias=db_alias, pred_query=pred_query
        )
        pred_query.id = record.record_id
        self._records[record_id] = record
        self._next_query_id += 1
        if pred_query.exec_result is not None and pred_query.exec_result.df is not None:
            await self._persist(record_id, pred_query.exec_result.df)
            self._in_memory.append(record_id)
            self._evict()
        return record

    async def get(self, record_id: str) -> QueryRecord:
        """Return a previously stored query record, hydrating spilled DFs."""
        try:
            record = self._records[record_id]
        except KeyError:
            raise KeyError(f"No query with id {record_id}") from None
        if record_id in self._spilled:
            await self._hydrate(record_id, record)
        return record

    async def last(self) -> QueryRecord:
        """Return the most recently stored query record."""
        if not self._records:
            raise ValueError("No query has been executed")
        return await self.get(f"Q{self._next_query_id - 1}")

    def attach_chart(self, record_id: str, vegalite_spec: dict[str, Any]) -> None:
        """Attach a Vega-Lite spec to an existing query record."""
        try:
            record = self._records[record_id]
        except KeyError:
            raise KeyError(f"No query with id {record_id}") from None
        record.vegalite_spec = vegalite_spec

    # -- spill / hydrate internals --

    async def _ensure_schema(self) -> None:
        """Create the spill schema once."""
        if self._schema_created or self._spill_connector is None:
            return
        await self._spill_connector.run_query_async(f'CREATE SCHEMA IF NOT EXISTS "{_QH_SCHEMA}"')
        self._schema_created = True

    async def _persist(self, record_id: str, df: pd.DataFrame) -> None:
        """Write a DF to the workspace DuckDB."""
        if self._spill_connector is None:
            return
        try:
            await self._ensure_schema()
            await self._spill_connector.write_dataframe_async(
                df=df,
                table_name=record_id,
                schema_name=_QH_SCHEMA,
                mode="replace",
            )
        except Exception:
            logger.warning("Failed to persist %s to workspace", record_id, exc_info=True)

    def _evict(self) -> None:
        """Remove oldest in-memory DFs until within the limit."""
        if not self._spill_connector:
            return
        while len(self._in_memory) > self._max_in_memory:
            oldest_id = self._in_memory.popleft()
            exec_result = self._records[oldest_id].pred_query.exec_result
            if exec_result is not None:
                exec_result.df = None
            self._spilled.add(oldest_id)

    async def _hydrate(self, record_id: str, record: QueryRecord) -> None:
        """Load a spilled DF back from the workspace DuckDB."""
        assert self._spill_connector is not None
        result = await self._spill_connector.run_query_async(f'SELECT * FROM "{_QH_SCHEMA}"."{record_id}"')
        record.pred_query.exec_result.df = result.df  # type: ignore[union-attr]
        self._spilled.discard(record_id)
        self._in_memory.append(record_id)
        self._evict()
