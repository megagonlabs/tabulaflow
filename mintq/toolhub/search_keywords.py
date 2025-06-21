from typing import ClassVar
from dataclasses import dataclass, field
from collections import defaultdict
import sqlalchemy
from sqlalchemy.sql import quoted_name
from sqlalchemy import select, distinct
from pydantic_ai import Tool
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter


@dataclass
class SearchKeywordsTool:
    name: ClassVar[str] = "search_keywords"
    db_connector: BaseAsyncSQLDBConnector
    formatter: BaseSQLSchemaFormatter
    metrics_: dict = field(default_factory=lambda: defaultdict(int))

    async def __call__(self, table: str, column: str, keywords: list[str]) -> str:
        """
        Search for values in a column of a table that match any of the keywords.

        Args:
            table: The name of the table to search in.
            column: The name of the column to search in. The datatype of the column must be text-like.
            keywords: A list of keywords to search for. A value is considered a match if it contains any of the keywords.
        """
        db_connector = self.db_connector

        # Remove the quote characters from the column name if they exist
        for quote_char in '"`':
            if column.startswith(quote_char) and column.endswith(quote_char):
                column = column[1:-1]
                break

        table_id_to_schema = {
            self.formatter.format_table_name(table_schema): table_schema for table_schema in self.db_connector.schema.tables
        }

        if table not in table_id_to_schema:
            self.metrics_["search_keywords_table_not_found"] += 1
            return f"(table {table} not found)"

        column_dtypes = {col.name: col.dtype for col in table_id_to_schema[table].columns}
        if column not in column_dtypes:
            self.metrics_["search_keywords_column_not_found"] += 1
            return f"(column {column} not found in table {table})"
        if column_dtypes[column] not in ("VARCHAR", "TEXT", "STRING"):
            self.metrics_["search_keywords_column_not_string"] += 1
            return f"(column {column} is not a string)"

        if "." in table:
            schema_name, table_name = table.split(".")
        else:
            schema_name, table_name = None, table
        column_name = quoted_name(column, quote=True)

        matches = []
        for keyword in keywords:
            sql_table = sqlalchemy.Table(
                table_name, sqlalchemy.MetaData(), sqlalchemy.Column(column_name, sqlalchemy.String), schema=schema_name
            )
            stmt = select(distinct(sql_table.c[column_name])).where(sql_table.c[column_name].like(f"%{keyword}%"))
            result = await db_connector.run_query_async(stmt, timeout=None)
            matches += [row[0] for row in result]
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
