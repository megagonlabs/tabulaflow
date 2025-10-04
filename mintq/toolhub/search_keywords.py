from typing import ClassVar
import sqlalchemy
from sqlalchemy.sql import quoted_name
from sqlalchemy import select
from pydantic import BaseModel
from pydantic_ai import Tool
from mintq.db_connector import BaseSQLDBConnector
from mintq.toolhub.utils import equals_ci


class SearchKeywordsToolMetrics(BaseModel):
    error_table_not_found: int = 0
    error_column_not_found: int = 0
    error_column_not_string: int = 0


class SearchKeywordsTool:
    name: ClassVar = "search_keywords"

    def __init__(self, db_connector: BaseSQLDBConnector):
        self.db_connector = db_connector
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
        db_connector = self.db_connector

        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [t.schema_name for t in self.db_connector.schema.tables]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        # Remove the quote characters from the column name if they exist
        for quote_char in '"`':
            if column_name.startswith(quote_char) and column_name.endswith(quote_char):
                column_name = column_name[1:-1]
                break

        table = None
        for t in self.db_connector.schema.tables:
            if equals_ci(t.schema_name, schema_name) and t.name.lower() == table_name.lower():
                table = t
                break

        if table is None:
            self._metrics.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        column = None
        for c in table.columns:
            if c.name.lower() == column_name.lower():
                if c.dtype not in ("VARCHAR", "TEXT", "STRING"):
                    self._metrics.error_column_not_string += 1
                    return f"(column {column_name} is not a string)"
                column = c
                break

        if column is None:
            self._metrics.error_column_not_found += 1
            return f"(column {column_name} not found in table {table_name} in schema {schema_name})"

        column_name = quoted_name(column_name, quote=True)
        matches = []
        for keyword in keywords:
            keyword = keyword.lower()
            sql_table = sqlalchemy.Table(
                table_name, sqlalchemy.MetaData(), sqlalchemy.Column(column_name, sqlalchemy.String), schema=schema_name
            )
            stmt = select(sql_table.c[column_name]).distinct().where(sql_table.c[column_name].ilike(f"%{keyword}%"))
            exec_result = await db_connector.run_query_async(stmt, timeout=None)
            if exec_result.df is None:
                raise ValueError(f"Query {stmt} failed: {exec_result.error}")
            matches += [row[0] for row in exec_result.df.itertuples()]
        matches = sorted(list(set(matches)))
        if not matches:
            return "(no matches found)"

        res = f"{len(matches)} matches:\n"
        res += "\n".join(matches[:10])
        if len(matches) > 10:
            res += "\n..."
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def get_metrics(self) -> SearchKeywordsToolMetrics:
        return self._metrics
