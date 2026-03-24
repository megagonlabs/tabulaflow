from typing import ClassVar
import pandas as pd
from pydantic_ai import Tool
from pydantic import BaseModel, Field
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import PredQuery
from mintq.formatters.utils import format_df
from mintq.toolhub.utils import format_sqlalchemy_error_msg
from mintq.config import mintq_config

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
        description="The parameter name that corresponds to the :<parameter_name> placeholder in the query."
    )
    parameter_value: int | float | str = Field(description="The intended value of the parameter.")


class RunQueryTool:
    """Execute a SQL query against the database and return formatted results.

    When ``allow_params=True``, the tool schema exposed to the LLM includes
    a ``parameters`` argument for parameterized queries (e.g. ``:threshold``).
    When ``False`` (the default), only the ``query`` argument is exposed.

    Args:
        db_connector: Database connector to execute queries against.
        allow_params: Whether to expose the ``parameters`` argument to the LLM.
        timeout: Query timeout in seconds. Defaults to ``mintq_config.query_timeout``.
        max_visible_rows: Maximum rows shown in the formatted output.
        max_cell_width: Maximum character width per cell in the formatted output.
        floatfmt: Float format string passed to tabulate.
    """

    name: ClassVar = "run_query"

    def __init__(
        self,
        db_connector: BaseSQLDBConnector,
        *,
        allow_params: bool = False,
        timeout: int | None | object = _UNSET,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        disconnect_on_finish: bool = False,
    ):
        self.db_connector = db_connector
        self.allow_params = allow_params
        self.timeout: int | None = mintq_config.query_timeout if timeout is _UNSET else timeout  # type: ignore
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._disconnect_on_finish = disconnect_on_finish
        self._metrics = RunQueryToolMetrics()
        self._last_pred_query: PredQuery | None = None

    async def _run_with_params(self, query: str, parameters: list[LLMParameter] = []) -> str:
        """Execute a SQL query and return the results.

        Returning large result sets is safe — the display is automatically truncated,
        and full execution results are always recorded.

        Procedural / anonymous blocks (e.g. ``DECLARE … BEGIN … END``,
        ``EXECUTE IMMEDIATE``) are supported.

        Example:
        ```python
        run_query(
            query="SELECT * FROM student WHERE gpa > :gpa_threshold",
            parameters=[{"parameter_name": "gpa_threshold", "parameter_value": 3.5}],
        )
        ```

        Args:
            query: The SQL query to execute.
            parameters: The parameters to use in the query. A list of dictionaries,
                each containing a `parameter_name` and a `parameter_value` field.
        """
        return await self._execute(query, parameters)

    async def _run_no_params(self, query: str) -> str:
        """Execute a SQL query and return the results.

        Returning large result sets is safe — the display is automatically truncated,
        and full execution results are always recorded.

        Procedural / anonymous blocks (e.g. ``DECLARE … BEGIN … END``,
        ``EXECUTE IMMEDIATE``) are supported.

        Args:
            query: The SQL query to execute.
        """
        return await self._execute(query, [])

    async def _execute(self, query: str, parameters: list[LLMParameter]) -> str:
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
            # if df.isnull().all().any():
            #     res += "\n(warning: a column is entirely null, the query might be incorrect)"

            return res
        finally:
            if self._disconnect_on_finish:
                await self.db_connector.disconnect_async()

    async def __call__(self, query: str, parameters: list[LLMParameter] | None = None) -> str:
        if parameters is not None:
            return await self._run_with_params(query, parameters)
        return await self._run_no_params(query)

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._run_with_params if self.allow_params else self._run_no_params
        return Tool(fn, name=self.name)

    def metrics(self) -> RunQueryToolMetrics:
        return self._metrics

    def last_pred_query(self) -> PredQuery:
        if self._last_pred_query is None:
            raise ValueError("No query has been executed")
        return self._last_pred_query