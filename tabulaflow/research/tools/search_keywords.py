from typing import ClassVar
import sqlalchemy
from sqlalchemy.sql import quoted_name
from sqlalchemy import select
from pydantic import BaseModel
from pydantic_ai import Tool
from tabulaflow.data import SQLConnector
from tabulaflow.agents.tools._sql import find_column, find_table


class SearchKeywordsToolMetrics(BaseModel):
    num_calls: int = 0
    error_table_not_found: int = 0
    error_column_not_found: int = 0
    error_column_not_string: int = 0


class SearchKeywordsTool:
    name: ClassVar = "search_keywords"

    def __init__(self, db_connector: SQLConnector, max_visible_results: int = 40):
        self.db_connector = db_connector
        self.max_visible_results = max_visible_results
        self._metrics = SearchKeywordsToolMetrics()

    async def __call__(self, schema_name: str | None, table_name: str, column_name: str, keywords: list[str]) -> str:
        """
        Search for values in a column of a table that match any of the keywords.

        Args:
            schema_name: The name of the schema to which the table belongs, or None if schema is not applicable.
            table_name: The name of the table to which the column belongs.
            column_name: The name of the column to search in. The datatype of the column must be text-like.
            keywords: A list of keywords to search for. A value is considered a match if it contains any of the keywords.
        """
        self._metrics.num_calls += 1
        db_connector = self.db_connector

        table = find_table(db_connector.schema, schema_name, table_name)
        if table is None:
            self._metrics.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        column = find_column(table, column_name)
        if column is None:
            self._metrics.error_column_not_found += 1
            return f"(column {column_name} not found in table {table_name} in schema {schema_name})"

        if column.dtype not in ("VARCHAR", "TEXT", "STRING"):
            self._metrics.error_column_not_string += 1
            return f"(column {column_name} is not a string)"

        physical_column_name = quoted_name(column.name, quote=True)
        matches = []
        for keyword in keywords:
            keyword = keyword.lower()
            sql_table = sqlalchemy.Table(
                table.name,
                sqlalchemy.MetaData(),
                sqlalchemy.Column(physical_column_name, sqlalchemy.String),
                schema=table.schema_name,
            )
            stmt = (
                select(sql_table.c[physical_column_name])
                .distinct()
                .where(sql_table.c[physical_column_name].ilike(f"%{keyword}%"))
            )
            exec_result = await db_connector.run_query_async(stmt, timeout=None)
            if exec_result.df is None:
                raise ValueError(f"Query {stmt} failed: {exec_result.error}")
            matches += [row[0] for row in exec_result.df.itertuples(index=False)]
        matches = sorted(list(set(matches)))
        if not matches:
            return "(no matches found)"

        res = f"{len(matches)} matches found:\n"
        if len(matches) <= self.max_visible_results:
            res += "\n".join(matches)
        else:
            half = self.max_visible_results // 2
            res += "\n".join(matches[:half])
            res += f"\n... ({len(matches) - self.max_visible_results} more) ...\n"
            res += "\n".join(matches[-(self.max_visible_results - half) :])
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> SearchKeywordsToolMetrics:
        return self._metrics
