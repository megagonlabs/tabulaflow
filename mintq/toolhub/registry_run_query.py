"""Run-query tool backed by a DBRegistry, letting agents target any source."""

from dataclasses import dataclass
from typing import ClassVar

from pydantic_ai import Tool

from mintq.config import mintq_config
from mintq.db_connector.db_registry import DBRegistry
from mintq.schema import PredQuery
from mintq.toolhub.run_query import LLMParameter, RunQueryTool, RunQueryToolMetrics
from mintq.toolhub.utils import sum_tool_metrics

_UNSET = object()


@dataclass
class QueryRecord:
    """Metadata for a query executed through the registry tool."""

    record_id: str
    db_alias: str
    pred_query: PredQuery


class QueryHistory:
    """In-memory store of queries executed during a session."""

    def __init__(self) -> None:
        self._records: dict[str, QueryRecord] = {}
        self._next_query_id = 1

    def add(self, db_alias: str, pred_query: PredQuery) -> QueryRecord:
        """Store a query and assign it the next opaque record ID."""
        record_id = f"Q{self._next_query_id}"
        record = QueryRecord(record_id=record_id, db_alias=db_alias, pred_query=pred_query)
        pred_query.id = record.record_id
        self._records[record_id] = record
        self._next_query_id += 1
        return record

    def get(self, query_id: str) -> QueryRecord:
        """Return a previously stored query record."""
        try:
            return self._records[query_id]
        except KeyError:
            raise KeyError(f"No query with id {query_id}") from None

    def last(self) -> QueryRecord:
        """Return the most recently stored query record."""
        if not self._records:
            raise ValueError("No query has been executed")
        return self._records[f"Q{self._next_query_id - 1}"]


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
        record = self._history.add(db_alias, pred_query)
        return f"[query_id={record.record_id}]\n{result}"

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

    def get_query_record(self, query_id: str) -> QueryRecord:
        """Return the record for a previously executed query.

        Args:
            query_id: The string ID assigned to the query at execution time.

        Raises:
            KeyError: If no query with ``query_id`` exists.
        """
        return self._history.get(query_id)
