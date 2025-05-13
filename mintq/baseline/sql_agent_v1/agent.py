from abc import ABC
import sqlalchemy
from sqlalchemy import select, distinct
from pydantic import BaseModel
from mintq.db_connector import BaseDBConnector
from mintq.schema_formatter import get_schema_formatter


class Action(ABC, BaseModel):
    pass


class RunQueryAction(Action):
    query: str


class ListColumnsAction(Action):
    table: str
    directory: str


class SearchKeywordsAction(Action):
    table: str
    column: str
    keywords: list[str]


class Environment:
    def __init__(self, db_connector: BaseDBConnector):
        self.db_connector = db_connector
        self.formatter = get_schema_formatter("sql_default")
        self.tables = {self.formatter.format_table_name(table): table for table in db_connector.get_tables()}

    @staticmethod
    def _truncate(s: str, max_length_chars: int) -> str:
        if len(s) <= max_length_chars:
            return s
        return s[: max_length_chars // 2] + "\n...content truncated...\n" + s[-max_length_chars // 2 :]

    def _run_query(self, query: str) -> str:
        exec_results = self.db_connector.run_query(query)
        if not exec_results:
            return "(query executed successfully, but results are empty)"
        exec_results = "\n".join([str(row) for row in exec_results])
        exec_results = self._truncate(exec_results, 500)
        return exec_results

    def _list_columns(self, table: str) -> str:
        table_schema = self.tables[table]
        if not table_schema.columns:
            return f"(table {table} has no columns)"
        return "\n".join([self.formatter.format_column(table_schema, col) for col in table_schema.columns])

    def _search_keywords(self, table: str, column: str, keywords: list[str]) -> str:
        matches = []
        for keyword in keywords:
            sql_table = sqlalchemy.Table(table, sqlalchemy.MetaData(), sqlalchemy.Column(column, sqlalchemy.String))
            stmt = select(distinct(sql_table.c[column])).where(sql_table.c[column].like(f"%{keyword}%"))
            with self.db_connector._engine.connect() as conn:
                result = conn.execute(stmt)
                matches += [row[0] for row in result]
        matches = sorted(list(set(matches)))
        if not matches:
            return "(no matches found)"
        
        res = f"{len(matches)} matches:\n"
        res += "\n".join(matches[:10])
        if len(matches) > 10:
            res += "\n..."
        return res

    def step(self, action: Action) -> str:
        if isinstance(action, RunQueryAction):
            return self._run_query(action.query)
        elif isinstance(action, ListColumnsAction):
            return self._list_columns(action.table)
        elif isinstance(action, SearchKeywordsAction):
            return self._search_keywords(action.table, action.column, action.keywords)
        else:
            raise ValueError(f"Unknown action: {action}")


class SQLAgentV1:
    pass
