from dataclasses import dataclass, field
from typing import ClassVar, cast
from collections import defaultdict
import pandas as pd
from pydantic_ai import Tool
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.toolhub.utils import format_df


@dataclass
class RunQueryTool:
    name: ClassVar[str] = "run_query"
    db_connector: BaseAsyncSQLDBConnector
    metrics_: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    async def __call__(self, query: str) -> str:
        """
        Execute a SQL query and return the results.

        Args:
            query: The SQL query to execute.
        """
        db_connector = self.db_connector
        try:
            df = await db_connector.run_query_async(query, return_df=True)
            df = cast(pd.DataFrame, df)
        except TimeoutError:
            return "(query timed out after 30 seconds)"
        except Exception as e:
            return f"(query failed: {e})"

        if df.empty:
            return "(Warning: query executed successfully, but results are empty, the query might be incorrect)"

        res = format_df(df, max_visible_rows=5)

        if df.isnull().all().any():
            res += "\n(Warning: a column is entirely null, the query might be incorrect)"
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
