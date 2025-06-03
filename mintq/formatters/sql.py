from typing import Optional
import collections
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema


class SQLDefaultSchemaFormatter:
    name = "sql_default"

    def __init__(self, quote_char: str = '"', example_max_chars: int = 100):
        self.quote_char = quote_char
        self.example_max_chars = example_max_chars

    def _quote(self, s: str) -> str:
        return f"{self.quote_char}{s}{self.quote_char}"

    def _quote_if_needed(self, s: str) -> str:
        return self._quote(s) if " " in s else s

    def _full_table_name(self, table: str, schema: Optional[str]) -> str:
        if schema is None:
            return self._quote_if_needed(table)
        else:
            return f"{self._quote_if_needed(schema)}.{self._quote_if_needed(table)}"

    def _truncate(self, s: str) -> str:
        if len(s) <= self.example_max_chars:
            return s
        return s[: self.example_max_chars // 2] + "..." + s[-self.example_max_chars // 2 :]

    def format_table_name(self, table: SQLTableSchema) -> str:
        return self._full_table_name(table.name, table.schema_name)

    def format(self, schema: SQLSchema, include_foreign_keys: bool = True, include_table_schemas: bool = True) -> str:
        table_id_to_fks = collections.defaultdict(list)
        for fk in schema.foreign_keys:
            table_id_to_fks[self._full_table_name(fk.table, fk.schema_name)].append(fk)

        res = f"Database: {schema.name}"
        for table in schema.tables:
            table_id = self._full_table_name(table.name, table.schema_name)
            res += f"\n* [Table] {table_id}"
            if table.primary_key:
                res += f"\n  - [Primary Key] {', '.join([self._quote_if_needed(pk) for pk in table.primary_key])}"
            if include_foreign_keys:
                for fk in table_id_to_fks[table_id]:
                    if len(fk.columns) > 1 or len(fk.foreign_columns) > 1:
                        raise ValueError(f"Multiple foreign keys are not supported: {fk}")
                    res += f"\n  - [Foreign Key] {fk.columns[0]} -> {self._full_table_name(fk.foreign_table, fk.foreign_schema_name)}.{self._quote_if_needed(fk.foreign_columns[0])}"

        if include_table_schemas:
            res += "\n\n"
            res += "\n\n".join([self.format_table(table) for table in schema.tables])
        return res

    def format_table(self, table: SQLTableSchema) -> str:
        res = f"Table details: {self._full_table_name(table.name, table.schema_name)} ({table.num_rows} rows)\n"
        if table.primary_key:
            res += f"Primary key: {', '.join([self._quote_if_needed(pk) for pk in table.primary_key])}\n"
        res += "\n".join([self.format_column(table, column) for column in table.columns])
        return res

    def format_column(self, table: SQLTableSchema, column: SQLColumnSchema) -> str:
        res = f"- {self._quote_if_needed(column.name)}: {column.dtype}"
        is_categorical = (
            column.dtype in ("TEXT", "VARCHAR")
            and 0 < len(column.examples) <= 20
            and len(column.examples) / table.num_rows < 0.01
        )
        if is_categorical:  # show all possible values
            valid_values = [self._quote(self._truncate(v)) for v in column.examples]
            valid_values = sorted(valid_values)
            res += " (Allowed values: {" + ", ".join(valid_values) + "})"
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
            example = self._truncate(example)
            res += f" (Example: {example})"
        return res
