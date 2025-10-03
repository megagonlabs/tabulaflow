from typing import ClassVar, Any
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.db_connector import BaseSQLDBConnector
from mintq.toolhub.utils import format_df


class RunQueryToolMetrics(BaseModel):
    error_timeout: int = 0
    error_query_failed: int = 0


class RunQueryTool:
    name: ClassVar = "run_query"

    def __init__(self, db_connector: BaseSQLDBConnector):
        self.db_connector = db_connector
        self._metrics = RunQueryToolMetrics()

    async def __call__(self, query: str, parameters: dict[str, Any] = {}) -> str:
        """
        Execute a SQL query and return the results.

        Args:
            query: The SQL query to execute.
            parameters: The parameters to use in the query.
        """
        db_connector = self.db_connector
        exec_result = await db_connector.run_query_async(query, parameters, timeout=30)
        if exec_result.df is None:
            if exec_result.error.exc_type == "TimeoutError":  # type: ignore
                self._metrics.error_timeout += 1
                return "(query timed out after 30 seconds)"
            else:
                self._metrics.error_query_failed += 1
                return f"(query failed: {exec_result.error})"

        df = exec_result.df
        if df.empty:
            return "(Warning: query executed successfully, but results are empty, the query might be incorrect)"

        res = format_df(df, max_visible_rows=5)

        if df.isnull().all().any():
            res += "\n(Warning: a column is entirely null, the query might be incorrect)"
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def get_metrics(self) -> RunQueryToolMetrics:
        return self._metrics
