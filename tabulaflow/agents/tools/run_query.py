from dataclasses import dataclass
from typing import Any, ClassVar, cast
import pandas as pd
from pydantic_ai import Tool
from pydantic import BaseModel, Field
from tabulaflow.core.results import ExecResult, GraphResult
from tabulaflow.data.protocols import DBConnector, SQLConnectorProtocol
from tabulaflow.output.formatting._core import format_dataframe
from tabulaflow.agents.tools._sql import format_sqlalchemy_error_msg
from tabulaflow.agents.tools.base import _omit_tool_parameters

_UNSET = object()


def _format_latency(seconds: float | None) -> str:
    """Render a query's execution latency as a compact string (``""`` when unknown).

    Sub-second timings are shown in milliseconds, larger ones in seconds.
    """
    if seconds is None:
        return ""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


def _detect_result_hints(df: pd.DataFrame) -> list[str]:
    """Detect common problematic result patterns and return actionable hints."""
    hints: list[str] = []
    cols_lower = [str(c).lower() for c in df.columns]

    # Snowflake anonymous block: single column named "anonymous block" with NULL
    if cols_lower == ["anonymous block"]:
        hints.append(
            "hint: The result contains only an 'anonymous block' column — this means the anonymous block "
            "(DECLARE … BEGIN … END) executed but did not return the inner query's result set. "
            "To fix this, declare a RESULTSET variable, assign it with `res := (EXECUTE IMMEDIATE :sql);`, "
            "and add `RETURN TABLE(res);` before END."
        )

    return hints


def _format_graph_result(graph: GraphResult | None) -> str:
    if graph is None:
        return ""
    node_word = "node" if len(graph.nodes) == 1 else "nodes"
    edge_word = "edge" if len(graph.edges) == 1 else "edges"
    return f"\n(Graph view: {len(graph.nodes):,} {node_word}, {len(graph.edges):,} {edge_word})"


class RunQueryToolMetrics(BaseModel):
    num_calls: int = 0
    error_timeout: int = 0
    error_query_failed: int = 0
    error_read_only_violation: int = 0


class LLMParameter(BaseModel):
    parameter_name: str = Field(
        description="The parameter name that corresponds to the placeholder in the query (e.g. :name in SQL, $name in Cypher)."
    )
    parameter_value: int | float | str = Field(description="The intended value of the parameter.")


@dataclass(frozen=True)
class QueryExecution:
    """Result of one run-query invocation."""

    output: str
    query: str
    parameter_values: dict[str, Any]
    exec_result: ExecResult


class RunQueryTool:
    """Execute a query against the database and return formatted results.

    Supports both SQL connectors (SQLite, Snowflake, MySQL, …) and property
    graph connectors (Neo4j via Cypher).

    When ``enable_params=True``, the tool schema exposed to the LLM includes
    a ``parameters`` argument for parameterized queries.
    When ``False`` (the default), only the ``query`` argument is exposed.

    When ``enable_refresh=True``, the tool schema also includes a ``refresh``
    flag that, when set by the LLM, re-introspects the connector's schema
    after the query runs.  Use this when the agent is allowed to issue DDL
    (``CREATE`` / ``DROP`` / ``ALTER``) and the connector's cached schema
    must reflect the new state for subsequent ``get_table_schema`` calls.

    Attributes:
        db_connector: Database connector to execute queries against.
        enable_params: Whether to expose the ``parameters`` argument to the LLM.
        enable_refresh: Whether to expose the ``refresh`` argument to the LLM.
        timeout: Query timeout in seconds. When omitted, use the connector default;
            ``None`` explicitly disables the timeout.
        max_visible_rows: Maximum rows shown in the formatted output.
        max_cell_width: Maximum character width per cell in the formatted output.
        floatfmt: Float format string passed to tabulate.
        release_connections_on_finish: Whether to release SQL connection-pool
            resources after each execution while keeping the connector usable.
    """

    name: ClassVar = "run_query"

    def __init__(
        self,
        db_connector: DBConnector,
        *,
        enable_params: bool = False,
        enable_refresh: bool = False,
        timeout: int | None | object = _UNSET,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        release_connections_on_finish: bool = False,
    ):
        if release_connections_on_finish and db_connector.connector_type != "sql":
            raise ValueError("release_connections_on_finish is only supported for SQL connectors")
        self.db_connector = db_connector
        self.enable_params = enable_params
        self.enable_refresh = enable_refresh
        self.timeout = timeout
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._release_connections_on_finish = release_connections_on_finish
        self._metrics = RunQueryToolMetrics()
        self._last_execution: QueryExecution | None = None

    async def execute(
        self, query: str, parameters: list[LLMParameter] | None = None, refresh: bool = False
    ) -> QueryExecution:
        """Execute one query and return both agent-facing output and recorded query data."""

        self._metrics.num_calls += 1
        parameters = parameters or []
        param_dict = {p.parameter_name: p.parameter_value for p in parameters}
        try:
            if self.timeout is _UNSET:
                exec_result = await self.db_connector.run_query_async(query, parameters=param_dict)
            else:
                exec_result = await self.db_connector.run_query_async(
                    query,
                    parameters=param_dict,
                    timeout=self.timeout,  # type: ignore[arg-type]
                )
            res = self._format_exec_result(exec_result)
            if refresh:
                try:
                    await self.db_connector.refresh_schema_async()
                    res += "\n(schema refreshed from live database)"
                except Exception as e:
                    res += f"\n(warning: schema refresh failed: {type(e).__name__}: {e})"
            execution = QueryExecution(output=res, query=query, parameter_values=param_dict, exec_result=exec_result)
            self._last_execution = execution
            return execution
        finally:
            if self._release_connections_on_finish:
                await cast(SQLConnectorProtocol, self.db_connector).release_connections_async()

    def _format_exec_result(self, exec_result: ExecResult) -> str:
        if exec_result.error is not None:
            if exec_result.error.exc_type == "ReadOnlyViolationError":
                self._metrics.error_read_only_violation += 1
                return f"(error: query failed: {exec_result.error.message})"
            elif exec_result.error.exc_type == "TimeoutError":
                self._metrics.error_timeout += 1
                return "(error: query timed out)"
            else:
                self._metrics.error_query_failed += 1
                return f"(error: query failed: {format_sqlalchemy_error_msg(exec_result.error.message)})"

        # Successful execution — surface the connector-measured latency as a trailing
        # line (omitted when the connector recorded none, e.g. older cached results).
        lat = _format_latency(exec_result.latency_seconds)
        lat_line = f"\n(latency: {lat})" if lat else ""
        graph_line = _format_graph_result(exec_result.graph)

        if exec_result.df is None:
            # A successful non-row-returning statement (DDL/DML). For DML the
            # driver reports a matched-row count; surface it so a no-op write
            # (0 rows) is visible rather than reading as a plain success.
            affected = exec_result.affected_rows
            if affected is None:
                return f"(statement executed successfully){lat_line}{graph_line}"
            if affected == 0:
                return f"(statement executed successfully, but 0 rows were affected — check the WHERE clause){lat_line}{graph_line}"
            return f"(statement executed successfully, {affected} row{'s' if affected != 1 else ''} affected){lat_line}{graph_line}"

        df = exec_result.df
        if df.empty:
            return f"(query executed successfully, but results are empty){lat_line}{graph_line}"

        res = format_dataframe(
            df, max_visible_rows=self.max_visible_rows, max_cell_width=self.max_cell_width, floatfmt=self.floatfmt
        )
        res += f"\n({len(df)} rows){lat_line}{graph_line}"
        res += f"\n\n(disaplay configuration: max_visible_rows={self.max_visible_rows}, max_cell_width={self.max_cell_width}, floatfmt='{self.floatfmt}'. Full execution results have been recorded.)"

        for hint in _detect_result_hints(df):
            res += f"\n({hint})"

        return res

    async def __call__(
        self,
        query: str,
        parameters: list[LLMParameter] | None = None,
        refresh: bool = False,
    ) -> str:
        """Execute a query against the database and return formatted results.

        Returning large result sets is safe: displayed output is truncated while
        the complete execution result remains available to the host.

        Args:
            query: The SQL or Cypher query to execute.
            parameters: Values for named query placeholders. Exposed only when
                parameterized queries are enabled.
            refresh: Whether to refresh connector schema after execution. Exposed
                only when schema refresh is enabled.
        """
        return (await self.execute(query, parameters, refresh and self.enable_refresh)).output

    def as_pydantic_ai_tool(self) -> Tool:
        omitted = []
        if not self.enable_params:
            omitted.append("parameters")
        if not self.enable_refresh:
            omitted.append("refresh")
        return Tool(self.__call__, name=self.name, prepare=_omit_tool_parameters(*omitted))

    def metrics(self) -> RunQueryToolMetrics:
        return self._metrics

    def last_execution(self) -> QueryExecution:
        if self._last_execution is None:
            raise ValueError("No query has been executed")
        return self._last_execution
