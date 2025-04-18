from rattq.schema_formatter.base import BaseSchemaFormatter
from rattq.schema import *


# class ForeignKeySchema(BaseModel):
#     table: str
#     column: str
#     foreign_table: str
#     foreign_column: str


# class SQLSchema(BaseDBSchema):
#     name: str
#     tables: List[SQLTableSchema]
#     foreign_keys: List[ForeignKeySchema]


class SQLDefaultSchemaFormatter(BaseSchemaFormatter):
    def __init__(self, quote_char: str = '"'):
        self.quote_char = quote_char

    def _quote(self, s: str) -> str:
        return f"{self.quote_char}{s}{self.quote_char}"

    def _quote_if_needed(self, s: str) -> str:
        return self._quote(s) if " " in s else s

    def _full_table_name(self, table: str, schema: Optional[str]) -> str:
        if schema is None:
            return self._quote_if_needed(table)
        else:
            return f"{self._quote_if_needed(schema)}.{self._quote_if_needed(table)}"

    def format(self, schema: SQLSchema) -> str:
        res = f"Database: {schema.name}\n"
        res += f"Tables: {', '.join([self._full_table_name(table.name, table.schema_name) for table in schema.tables])}\n"
        res += f"Foreign keys:\n"
        for fk in schema.foreign_keys:
            res += f"- {self._full_table_name(fk.table, fk.schema_name)}.{self._quote_if_needed(fk.columns[0])} -> {self._full_table_name(fk.foreign_table, fk.foreign_schema_name)}.{self._quote_if_needed(fk.foreign_columns[0])}\n"
        res += "\n"
        res += "\n\n".join([self._format_table(table) for table in schema.tables])
        return res

    def _format_table(self, table: SQLTableSchema) -> str:
        res = f"Table: {self._full_table_name(table.name, table.schema_name)} ({table.num_rows} rows)"
        res += f" (Primary key: {', '.join([self._quote_if_needed(pk) for pk in table.primary_key])})\n"
        res += "\n".join([self._format_column(column) for column in table.columns])
        return res

    def _format_column(self, column: SQLColumnSchema) -> str:
        res = f"- {self._quote_if_needed(column.name)}: {column.type}"
        is_categorical = column.type == "TEXT" and column.cardinality <= 10 and column.cardinality / column.count < 0.01
        if is_categorical:  # show all possible values
            res += " (Allowed values: {" + ", ".join([self._quote(v) for v in column.examples]) + "})"
        elif not column.examples:
            res += " (all values are null)"
        else:
            example = column.examples[0]
            if isinstance(example, str):
                example = self._quote(example)
            elif isinstance(example, float):
                example = f"{example:.3f}"
            else:
                example = str(example)
            res += f" (Example: {example})"
        return res
