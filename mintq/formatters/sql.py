from typing import ClassVar
from dataclasses import dataclass
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema


@dataclass
class SQLDefaultSchemaFormatter:
    name: ClassVar[str] = "sql_default"
    quote_char: str = '"'
    example_max_chars: int = 100

    def _quote(self, s: str) -> str:
        return f"{self.quote_char}{s}{self.quote_char}"

    def _quote_if_needed(self, s: str | None) -> str:
        if s is None:
            return "NULL"
        return self._quote(s) if " " in s else s

    def _full_table_name(self, table: str, schema: str | None) -> str:
        if schema is None:
            return self._quote_if_needed(table)
        else:
            return f"{self._quote_if_needed(schema)}.{self._quote_if_needed(table)}"

    def format_table_name(self, table: SQLTableSchema) -> str:
        return self._full_table_name(table.name, table.schema_name)

    def _truncate(self, s: str) -> str:
        if len(s) <= self.example_max_chars:
            return s
        return s[: self.example_max_chars // 2] + "..." + s[-self.example_max_chars // 2 :]

    def format(self, schema: SQLSchema, pk_fk_column_only: bool = False, add_description: bool = False) -> str:
        res = f"Database: {schema.name}"
        if not schema.tables:
            return f"{res}\n(database has no tables)"
        res += "\n\n"
        res += "\n\n".join([self.format_table(table, pk_fk_column_only, add_description) for table in schema.tables])
        return res

    def format_table(self, table: SQLTableSchema, pk_fk_column_only: bool = False, add_description: bool = False) -> str:
        res = f"=== (SCHEMA: {self._quote_if_needed(table.schema_name)}) TABLE: {self._quote_if_needed(table.name)} ({table.num_rows} rows) ===\n"

        composite_fks = []
        for fk in table.foreign_keys:
            if len(fk.columns) > 1:
                columns = "(" + ", ".join([self._quote_if_needed(c) for c in fk.columns]) + ")"
                fk_columns = "(" + ", ".join([self._quote_if_needed(c) for c in fk.foreign_columns]) + ")"
                fk_table = self._full_table_name(fk.foreign_table, fk.foreign_schema_name)
                composite_fks.append(f"* {columns} -> {fk_table}.{fk_columns}")
        if composite_fks:
            res += "[Composite FKs]\n" + "\n".join(composite_fks) + "\n\n"

        res += "\n".join(
            [
                self.format_column(column, add_description)
                for column in table.columns
                if not pk_fk_column_only or column.primary_key_type or column.foreign_keys
            ]
        )
        res += "\n=== END OF TABLE ==="
        return res

    def format_column(self, column: SQLColumnSchema, add_description: bool = False) -> str:
        res = f"- {self._quote_if_needed(column.name)}: {column.dtype}"
        if column.null_ratio == 1.0:
            res += " (all values are null)"
        elif column.null_ratio > 0.0:
            res += " NULLABLE"
        is_categorical = (
            column.dtype in ("TEXT", "VARCHAR", "ENUM")
            and column.num_unique
            and column.unique_ratio
            and 0 < column.num_unique <= 20
            and column.unique_ratio < 0.01
        )
        if is_categorical:  # show all possible values
            valid_values = [self._quote(self._truncate(v)) for v in column.examples]
            valid_values = sorted(valid_values)
            res += " {" + ", ".join(valid_values) + "}"
        elif column.examples:
            example = column.examples[0]
            if isinstance(example, str):
                example = self._quote(example)
            elif isinstance(example, float):
                example = f"{example:.3f}"
            else:
                example = str(example)
            example = self._truncate(example)
            res += f" (e.g. {example})"

        if column.primary_key_type:
            res += " [PK]" if column.primary_key_type == "single" else " [PK-composite]"
        for fk in column.foreign_keys:
            is_composite_fk = len(fk.columns) > 1
            res += (
                f" [FK -> {self._full_table_name(fk.foreign_table, fk.foreign_schema_name)}.{self._quote_if_needed(fk.foreign_columns[0])}]"
                if not is_composite_fk
                else " [FK-composite]"
            )

        if add_description and column.description:
            res += f" /* {column.description} */"
        return res
