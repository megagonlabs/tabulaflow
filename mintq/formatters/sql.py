from typing import Optional, ClassVar
from dataclasses import dataclass
import collections
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema


@dataclass
class SQLDefaultSchemaFormatter:
    name: ClassVar[str] = "sql_default"
    quote_char: str = '"'
    example_max_chars: int = 100

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

    def format(self, schema: SQLSchema) -> str:
        res = f"Database: {schema.name}"
        res += "\n\n"
        res += "\n\n".join([self.format_table(table) for table in schema.tables])
        return res

    def format_table(self, table: SQLTableSchema) -> str:
        for fk in table.foreign_keys:
            if len(fk.columns) > 1:
                raise NotImplementedError(f"Composite foreign keys are not supported: {fk.columns} in TABLE{table.name}")

        res = f"=== TABLE: {self._full_table_name(table.name, table.schema_name)} ===\n"
        res += "\n".join([self.format_column(column) for column in table.columns])
        res += "\n=== END OF TABLE ==="
        return res

    def format_column(self, column: SQLColumnSchema) -> str:
        res = f"- {self._quote_if_needed(column.name)}: {column.dtype}"
        is_categorical = (
            column.dtype in ("TEXT", "VARCHAR") and 0 < column.num_unique <= 20 and column.unique_ratio < 0.01
        )
        if is_categorical:  # show all possible values
            valid_values = [self._quote(self._truncate(v)) for v in column.examples]
            valid_values = sorted(valid_values)
            res += " {" + ", ".join(valid_values) + "}"
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
            res += f" (e.g. {example})"

        if column.primary_key_type:
            res += " [PK]" if column.primary_key_type == "single" else " [PK-composite]"
        for fk in column.foreign_keys:
            is_composite_fk = len(fk.columns) > 1
            res += (
                f" [FK: -> {self._full_table_name(fk.foreign_table, fk.foreign_schema_name)}.{self._quote_if_needed(fk.foreign_columns[0])}]"
                if not is_composite_fk
                else " [FK-composite]"
            )
        return res
