from rattq.schema_formatter.base import BaseSchemaFormatter
from rattq.schema import *


class SQLDefaultSchemaFormatter(BaseSchemaFormatter):
    def __init__(self, quote_char: str = '"'):
        self.quote_char = quote_char

    def _quote(self, s: str) -> str:
        return f"{self.quote_char}{s}{self.quote_char}"

    def _quote_if_needed(self, s: str) -> str:
        return self._quote(s) if " " in s else s

    def format(self, schema: SQLSchema) -> str:
        return "\n\n".join([self._format_table(table) for table in schema.tables])

    def _format_table(self, table: SQLTableSchema) -> str:
        res = f"Table: {self._quote_if_needed(table.name)} ({table.num_rows} rows)"
        res += f" (Primary key: {', '.join([self._quote_if_needed(pk) for pk in table.primary_key])})\n"
        res += "\n".join([self._format_column(column) for column in table.columns])
        return res

    def _format_column(self, column: SQLColumnSchema) -> str:
        res = f"- {self._quote_if_needed(column.name)}: {column.type}"
        is_categorical = (
            column.type == "TEXT"
            and column.cardinality <= 10
            and column.cardinality / column.count < 0.01
        )
        if is_categorical:  # show all possible values
            res += (
                " (Allowed values: {"
                + ", ".join([self._quote(v) for v in column.examples])
                + "})"
            )
        else:
            example = column.examples[0]
            if isinstance(example, str):
                example = self._quote(example)
            res += f" (Example: {example})"
        return res
