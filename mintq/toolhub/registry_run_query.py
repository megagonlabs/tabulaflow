"""Run-query tool backed by a DBRegistry, letting agents target any source."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic_ai import Tool

from mintq.config import mintq_config
from mintq.db_connector.db_registry import DBRegistry
from mintq.schema import PredQuery
from mintq.toolhub.run_query import LLMParameter, RunQueryTool, RunQueryToolMetrics
from mintq.toolhub.utils import sum_tool_metrics

if TYPE_CHECKING:
    import pandas as pd

    from mintq.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

_UNSET = object()

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
        max_in_memory: int = 1,
        spill_connector: SQLConnector | None = None,
    ) -> None:
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
                df=df, table_name=record_id, schema_name=_QH_SCHEMA, mode="replace",
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
        result = await self._spill_connector.run_query_async(
            f'SELECT * FROM "{_QH_SCHEMA}"."{record_id}"'
        )
        record.pred_query.exec_result.df = result.df  # type: ignore[union-attr]
        self._spilled.discard(record_id)
        self._in_memory.append(record_id)
        self._evict()


class RegistryRunQueryTool:
    """Execute a query against any registered database.

    The agent specifies which database to target via ``db_alias``.  The tool
    resolves the alias through a ``DBRegistry`` and delegates execution to a
    per-alias ``RunQueryTool`` instance.
    """

    name: ClassVar = "run_query"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        enable_params: bool = False,
        timeout: int | None | object = _UNSET,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        history: QueryHistory | None = None,
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            enable_params: Whether to expose the ``parameters`` argument to
                the LLM.
            timeout: Query timeout in seconds.  Defaults to
                ``mintq_config.query_timeout``.
            max_visible_rows: Maximum rows shown in the formatted output.
            max_cell_width: Maximum character width per cell in the formatted
                output.
            floatfmt: Float format string passed to tabulate.
            history: Optional shared query-history store. If not provided, the
                tool creates its own in-memory history.
        """
        self.registry = registry
        self.enable_params = enable_params
        self.timeout: int | None = mintq_config.query_timeout if timeout is _UNSET else timeout  # type: ignore[assignment]
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._tools: dict[str, RunQueryTool] = {}
        self._history = history or QueryHistory()

    def _get_tool(self, db_alias: str) -> RunQueryTool:
        """Return a cached ``RunQueryTool`` for ``db_alias``, creating one if needed."""
        tool = self._tools.get(db_alias)
        if tool is not None:
            return tool
        connector = self.registry.get(db_alias)
        tool = RunQueryTool(
            connector,
            enable_params=self.enable_params,
            timeout=self.timeout,
            max_visible_rows=self.max_visible_rows,
            max_cell_width=self.max_cell_width,
            floatfmt=self.floatfmt,
        )
        self._tools[db_alias] = tool
        return tool

    async def _run_with_params(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] = [],
    ) -> str:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
            parameters: Query parameters.  A list of dictionaries, each
                containing a ``parameter_name`` and a ``parameter_value`` field.
        """
        return await self._execute(db_alias, query, parameters)

    async def _run_no_params(self, db_alias: str, query: str) -> str:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
        """
        return await self._execute(db_alias, query, [])

    async def _execute(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter],
    ) -> str:
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"
        result = await tool(query, parameters)
        pred_query = tool.last_pred_query()
        record = await self._history.add(db_alias, tool.db_connector.connector_type, pred_query)
        return f"[record_id={record.record_id}]\n{result}"

    async def __call__(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] | None = None,
    ) -> str:
        if parameters is not None:
            return await self._run_with_params(db_alias, query, parameters)
        return await self._run_no_params(db_alias, query)

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._run_with_params if self.enable_params else self._run_no_params
        return Tool(fn, name=self.name)

    def metrics(self) -> RunQueryToolMetrics:
        """Return aggregated metrics across all aliases."""
        return sum_tool_metrics((t.metrics() for t in self._tools.values()), RunQueryToolMetrics)

    async def get_query_record(self, record_id: str) -> QueryRecord:
        """Return the record for a previously executed query.

        Args:
            record_id: The string ID assigned to the query record at execution time.

        Raises:
            KeyError: If no query with ``record_id`` exists.
        """
        return await self._history.get(record_id)
