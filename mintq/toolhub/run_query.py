from dataclasses import dataclass, field
from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.toolhub.utils import format_df


class RunQueryToolMetrics(BaseModel):
    error_timeout: int = 0
    error_query_failed: int = 0


@dataclass
class RunQueryTool:
    name: ClassVar[str] = "run_query"
    db_connector: BaseAsyncSQLDBConnector
    metrics_: RunQueryToolMetrics = field(default_factory=RunQueryToolMetrics)

    async def __call__(self, query: str) -> str:
        """
        Execute a SQL query and return the results.

        Args:
            query: The SQL query to execute.
        """
        db_connector = self.db_connector
        exec_result = await db_connector.run_query_async(query, timeout=30)
        if exec_result.df is None:
            if "timed out" in exec_result.error:  # type: ignore
                self.metrics_.error_timeout += 1
                return "(query timed out after 30 seconds)"
            else:
                self.metrics_.error_query_failed += 1
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
