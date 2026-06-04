from typing import Any, ClassVar
import pandas as pd
from pydantic_ai import Tool
from pydantic import BaseModel, Field
from tabulaflow.db_connector import NL2QDBConnector
from tabulaflow.schema import PredQuery
from tabulaflow.utils import format_df
from tabulaflow.toolhub.utils import format_sqlalchemy_error_msg
from tabulaflow.config import tabulaflow_config

_UNSET = object()


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
        timeout: Query timeout in seconds. Defaults to ``tabulaflow_config.query_timeout``.
        max_visible_rows: Maximum rows shown in the formatted output.
        max_cell_width: Maximum character width per cell in the formatted output.
        floatfmt: Float format string passed to tabulate.
    """

    name: ClassVar = "run_query"

    def __init__(
        self,
        db_connector: NL2QDBConnector,
        *,
        enable_params: bool = False,
        enable_refresh: bool = False,
        timeout: int | None | object = _UNSET,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        disconnect_on_finish: bool = False,
    ):
        self.db_connector = db_connector
        self.enable_params = enable_params
        self.enable_refresh = enable_refresh
        self.timeout: int | None = tabulaflow_config.query_timeout if timeout is _UNSET else timeout  # type: ignore
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._disconnect_on_finish = disconnect_on_finish
        self._metrics = RunQueryToolMetrics()
        self._last_pred_query: PredQuery | None = None

    async def _run_with_params_with_refresh(
        self, query: str, parameters: list[LLMParameter] = [], refresh: bool = False
    ) -> str:
        """Execute a query against the database and return the results.

        Returning large result sets is safe — the display is automatically truncated,
        and full execution results are always recorded.

        Procedural / anonymous blocks (e.g. ``DECLARE … BEGIN … END``,
        ``EXECUTE IMMEDIATE``) are supported for SQL dialects.

        Example:
        ```python
        run_query(
            query="SELECT * FROM student WHERE gpa > :gpa_threshold",
            parameters=[{"parameter_name": "gpa_threshold", "parameter_value": 3.5}],
        )
        ```

        Args:
            query: The query to execute.
            parameters: The parameters to use in the query. A list of dictionaries,
                each containing a `parameter_name` and a `parameter_value` field.
            refresh: If True, re-introspect the connector's schema after
                the query. Use only when the query changes the schema (DDL:
                ``CREATE`` / ``DROP`` / ``ALTER``). Triggers a full schema
                rebuild — be conservative on large cloud warehouses (e.g.
                Snowflake).
        """
        return await self._execute(query, parameters, refresh)

    async def _run_with_params(self, query: str, parameters: list[LLMParameter] = []) -> str:
        """Execute a query against the database and return the results.

        Returning large result sets is safe — the display is automatically truncated,
        and full execution results are always recorded.

        Procedural / anonymous blocks (e.g. ``DECLARE … BEGIN … END``,
        ``EXECUTE IMMEDIATE``) are supported for SQL dialects.

        Example:
        ```python
        run_query(
            query="SELECT * FROM student WHERE gpa > :gpa_threshold",
            parameters=[{"parameter_name": "gpa_threshold", "parameter_value": 3.5}],
        )
        ```

        Args:
            query: The query to execute.
            parameters: The parameters to use in the query. A list of dictionaries,
                each containing a `parameter_name` and a `parameter_value` field.
        """
        return await self._execute(query, parameters, False)

    async def _run_no_params_with_refresh(self, query: str, refresh: bool = False) -> str:
        """Execute a query against the database and return the results.

        Returning large result sets is safe — the display is automatically truncated,
        and full execution results are always recorded.

        Procedural / anonymous blocks (e.g. ``DECLARE … BEGIN … END``,
        ``EXECUTE IMMEDIATE``) are supported for SQL dialects.

        Args:
            query: The query to execute.
            refresh: If True, re-introspect the connector's schema after
                the query. Use only when the query changes the schema (DDL:
                ``CREATE`` / ``DROP`` / ``ALTER``). Triggers a full schema
                rebuild — be conservative on large cloud warehouses (e.g.
                Snowflake).
        """
        return await self._execute(query, [], refresh)

    async def _run_no_params(self, query: str) -> str:
        """Execute a query against the database and return the results.

        Returning large result sets is safe — the display is automatically truncated,
        and full execution results are always recorded.

        Procedural / anonymous blocks (e.g. ``DECLARE … BEGIN … END``,
        ``EXECUTE IMMEDIATE``) are supported for SQL dialects.

        Args:
            query: The query to execute.
        """
        return await self._execute(query, [], False)

    async def _execute(self, query: str, parameters: list[LLMParameter], refresh: bool) -> str:
        self._metrics.num_calls += 1
        param_dict = {p.parameter_name: p.parameter_value for p in parameters}
        try:
            exec_result = await self.db_connector.run_query_async(
                query,
                parameters=param_dict,
                timeout=self.timeout,
            )
            self._last_pred_query = PredQuery(
                query=query,
                parameter_names=[p.parameter_name for p in parameters],
                parameter_values=param_dict,
                exec_result=exec_result,
            )
            res = self._format_exec_result(exec_result)
            if refresh:
                try:
                    await self.db_connector.refresh_schema_async()
                    res += "\n(schema refreshed from live database)"
                except Exception as e:
                    res += f"\n(warning: schema refresh failed: {type(e).__name__}: {e})"
            return res
        finally:
            if self._disconnect_on_finish:
                await self.db_connector.disconnect_async()

    def _format_exec_result(self, exec_result: Any) -> str:
        if exec_result.df is None:
            assert exec_result.error is not None
            if exec_result.error.exc_type == "ReadOnlyViolationError":
                self._metrics.error_read_only_violation += 1
                return f"(query failed: {exec_result.error.message})"
            elif exec_result.error.exc_type == "TimeoutError":
                self._metrics.error_timeout += 1
                return "(query timed out)"
            else:
                self._metrics.error_query_failed += 1
                return f"(query failed: {format_sqlalchemy_error_msg(exec_result.error.message)})"

        df = exec_result.df
        if df.empty:
            return "(warning: query executed successfully, but results are empty, the query might be incorrect)"

        res = format_df(
            df, max_visible_rows=self.max_visible_rows, max_cell_width=self.max_cell_width, floatfmt=self.floatfmt
        )
        res += f"\n({len(df)} rows)"
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
        return await self._execute(query, parameters or [], refresh and self.enable_refresh)

    def as_pydantic_ai_tool(self) -> Tool:
        fn: Any
        if self.enable_params:
            fn = self._run_with_params_with_refresh if self.enable_refresh else self._run_with_params
        else:
            fn = self._run_no_params_with_refresh if self.enable_refresh else self._run_no_params
        return Tool(fn, name=self.name)

    def metrics(self) -> RunQueryToolMetrics:
        return self._metrics

    def last_pred_query(self) -> PredQuery:
        if self._last_pred_query is None:
            raise ValueError("No query has been executed")
        return self._last_pred_query
