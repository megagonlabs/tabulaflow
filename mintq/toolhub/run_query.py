from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel, Field
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import PredQuery
from mintq.formatters.utils import format_df
from mintq.toolhub.utils import format_sqlalchemy_error_msg


class RunQueryToolMetrics(BaseModel):
    num_calls: int = 0
    error_timeout: int = 0
    error_query_failed: int = 0


class LLMParameter(BaseModel):
    parameter_name: str = Field(
        description="The parameter name that corresponds to the :<parameter_name> placeholder in the query."
    )
    parameter_value: int | float | str = Field(description="The intended value of the parameter.")


class RunQueryWithParamsTool:
    name: ClassVar = "run_query"

    def __init__(self, db_connector: BaseSQLDBConnector, timeout: int | None = 90, max_visible_rows: int = 20):
        self.db_connector = db_connector
        self.timeout = timeout
        self.max_visible_rows = max_visible_rows
        self._metrics = RunQueryToolMetrics()
        self._last_pred_query: PredQuery | None = None

    async def __call__(self, query: str, parameters: list[LLMParameter] = []) -> str:
        """
        Execute a SQL query and return the results.

        Example:
        ```python
        run_query(
            query="SELECT * FROM student WHERE gpa > :gpa_threshold",
            parameters=[{"parameter_name": "gpa_threshold", "parameter_value": 3.5}],
        )
        ```

        Args:
            query: The SQL query to execute.
            parameters: The parameters to use in the query. A list of dictionaries, each containing a `parameter_name` and a `parameter_value` field.
        """
        self._metrics.num_calls += 1
        db_connector = self.db_connector
        exec_result = await db_connector.run_query_async(
            query,
            parameters={p.parameter_name: p.parameter_value for p in parameters},
            timeout=self.timeout,
        )
        self._last_pred_query = PredQuery(
            query=query,
            parameter_names=[p.parameter_name for p in parameters],
            parameter_values={p.parameter_name: p.parameter_value for p in parameters},
            exec_result=exec_result,
        )
        if exec_result.df is None:
            assert exec_result.error is not None
            if exec_result.error.exc_type == "TimeoutError":
                self._metrics.error_timeout += 1
                return f"(query timed out after {self.timeout} seconds)"
            else:
                self._metrics.error_query_failed += 1
                return f"(query failed: {format_sqlalchemy_error_msg(exec_result.error.message)})"

        df = exec_result.df
        if df.empty:
            return "(warning: query executed successfully, but results are empty, the query might be incorrect)"

        res = format_df(df, max_visible_rows=self.max_visible_rows)
        res += f"\n({len(df)} rows)"

        if df.isnull().all().any():
            res += "\n(warning: a column is entirely null, the query might be incorrect)"
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> RunQueryToolMetrics:
        return self._metrics

    def last_pred_query(self) -> PredQuery:
        if self._last_pred_query is None:
            raise ValueError("No query has been executed")
        return self._last_pred_query


class RunQueryNoParamsTool:
    name: ClassVar = "run_query"

    def __init__(self, db_connector: BaseSQLDBConnector, timeout: int | None = 90, max_visible_rows: int = 20):
        self.db_connector = db_connector
        self.timeout = timeout
        self.max_visible_rows = max_visible_rows
        self._metrics = RunQueryToolMetrics()
        self._last_pred_query: PredQuery | None = None

    async def __call__(self, query: str) -> str:
        """
        Execute a SQL query and return the results.

        Args:
            query: The SQL query to execute.
        """
        self._metrics.num_calls += 1
        db_connector = self.db_connector
        exec_result = await db_connector.run_query_async(
            query,
            timeout=self.timeout,
        )
        self._last_pred_query = PredQuery(
            query=query,
            exec_result=exec_result,
        )
        if exec_result.df is None:
            assert exec_result.error is not None
            if exec_result.error.exc_type == "TimeoutError":
                self._metrics.error_timeout += 1
                return f"(query timed out after {self.timeout} seconds)"
            else:
                self._metrics.error_query_failed += 1
                return f"(query failed: {format_sqlalchemy_error_msg(exec_result.error.message)})"

        df = exec_result.df
        if df.empty:
            return "(warning: query executed successfully, but results are empty, the query might be incorrect)"

        res = format_df(df, max_visible_rows=self.max_visible_rows)
        res += f"\n({len(df)} rows)"
        if len(df) > self.max_visible_rows:
            res += "\n(note: the complete results have been recorded)"

        # if df.isnull().all().any():
        #     res += "\n(warning: a column is entirely null, the query might be incorrect)"
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> RunQueryToolMetrics:
        return self._metrics

    def last_pred_query(self) -> PredQuery:
        if self._last_pred_query is None:
            raise ValueError("No query has been executed")
        return self._last_pred_query
