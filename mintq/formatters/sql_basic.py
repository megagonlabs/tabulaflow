from typing import ClassVar
from dataclasses import dataclass
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema
from mintq.formatters.base import formatter_registry
from mintq.formatters.utils import flatten_multiline


@formatter_registry.register
@dataclass
class SQLBasicSchemaFormatter:
    name: ClassVar[str] = "sql_basic"
    quote_char: str = '"'
    always_quote_columns: bool = True
    example_max_chars: int = 100
    floatfmt: str = ".8g"
    max_total_columns: int | None = None

    def _quote(self, s: str) -> str:
        return f"{self.quote_char}{s}{self.quote_char}"

    def _quote_if_needed(self, s: str | None) -> str:
        if s is None:
            return "NULL"
        # Quote if contains spaces, special chars, or is a reserved word
        if " " in s or "-" in s or not s.isidentifier():
            return self._quote(s)
        return s

    def _quote_column(self, s: str) -> str:
        if self.always_quote_columns:
            return self._quote(s)
        return self._quote_if_needed(s)

    def _full_table_name(self, table: str, schema: str | None) -> str:
        if schema is None:
            return self._quote_if_needed(table)
        else:
            return f"{self._quote_if_needed(schema)}.{self._quote_if_needed(table)}"

    def format_table_name(self, table: SQLTableSchema) -> str:
        return self._full_table_name(table.name, table.schema_name)

    def format_value(self, value: object) -> str:
        """Format a single value for display."""
        if isinstance(value, str):
            return self._quote(self._truncate(value))
        elif isinstance(value, float):
            return f"{value:{self.floatfmt}}"
        else:
            return str(value)

    def _truncate(self, s: str) -> str:
        s = flatten_multiline(s)
        if len(s) <= self.example_max_chars:
            return s
        return s[: self.example_max_chars // 2] + "..." + s[-self.example_max_chars // 2 :]

    def _compute_column_quotas(self, tables: list[SQLTableSchema]) -> list[int | None]:
        """Compute equal per-table column quotas from max_total_columns."""
        if self.max_total_columns is None:
            return [None] * len(tables)
        if not tables:
            return []
        quota = max(1, self.max_total_columns // len(tables))
        return [quota] * len(tables)

    def format(self, schema: SQLSchema, pk_fk_column_only: bool = False, add_description: bool = False) -> str:
        res = f"Database: {schema.name}"
        if schema.dialect:
            res += f" (SQL Dialect: {schema.dialect})"
        if not schema.tables:
            return f"{res}\n(database has no tables)"
        res += "\n\n"
        quotas = self._compute_column_quotas(schema.tables)
        res += "\n\n".join(
            [
                self.format_table(table, pk_fk_column_only, add_description, max_columns=max_columns)
                for table, max_columns in zip(schema.tables, quotas)
            ]
        )
        return res

    def format_table(
        self,
        table: SQLTableSchema,
        pk_fk_column_only: bool = False,
        add_description: bool = False,
        max_columns: int | None = None,
    ) -> str:
        res = f"(SCHEMA: {self._quote_if_needed(table.schema_name)}) TABLE:"
        if table.name_patterns:  # This is a compressed table
            pattern_strs = []
            for pattern in table.name_patterns:
                p = self._quote_if_needed(pattern.pattern)
                if pattern.comment:
                    p += f" ({pattern.comment})"
                pattern_strs.append(p)
            res += " " + ", ".join(pattern_strs)
        else:
            res += f" {self._quote_if_needed(table.name)}"
        if table.num_rows is not None:
            res += f" ({table.num_rows} rows)"
        res = f"=== {res} ===\n"

        composite_fks = []
        for fk in table.foreign_keys:
            if len(fk.columns) > 1:
                fk_cols = "(" + ", ".join([self._quote_column(c) for c in fk.columns]) + ")"
                ref_table = self._full_table_name(fk.foreign_table, fk.foreign_schema_name)
                ref_cols = "(" + ", ".join([self._quote_column(c) for c in fk.foreign_columns]) + ")"
                composite_fks.append(f"* {fk_cols} -> {ref_table}.{ref_cols}")
        if composite_fks:
            res += "[Composite FKs]\n" + "\n".join(composite_fks) + "\n\n"

        columns = [col for col in table.columns if not pk_fk_column_only or col.primary_key_type or col.foreign_keys]

        # Truncate columns if max_columns is set
        omitted_count = 0
        if max_columns is not None and len(columns) > max_columns:
            omitted_count = len(columns) - max_columns
            columns = columns[:max_columns]

        column_lines = [self.format_column(column, add_description) for column in columns]
        if omitted_count > 0:
            column_lines.append(f"  ... {omitted_count} more columns omitted")
        res += "\n".join(column_lines)
        res += "\n=== END OF TABLE ==="
        return res

    def format_column(self, column: SQLColumnSchema, add_description: bool = False) -> str:
        res = f"- {self._quote_column(column.name)}: {column.dtype}"
        if column.null_ratio is not None and column.null_ratio == 1.0:
            res += " (all values are null)"
        elif column.null_ratio is None or column.null_ratio > 0.0:
            res += " NULLABLE"
        is_categorical = (
            column.dtype in ("TEXT", "VARCHAR", "STRING", "ENUM")
            and column.num_unique is not None
            and column.unique_ratio is not None
            and (0 < column.num_unique <= 10 or (0 < column.num_unique <= 20 and column.unique_ratio < 0.01))
        )
        if is_categorical:  # show all possible values
            valid_values = sorted(self.format_value(v) for v in column.examples)
            res += " {" + ", ".join(valid_values) + "}"
        elif column.examples:
            res += f" (e.g. {self.format_value(column.examples[0])})"

        if column.primary_key_type:
            res += " [PK]" if column.primary_key_type == "single" else " [PK-composite]"
        for fk in column.foreign_keys:
            is_composite_fk = len(fk.columns) > 1
            res += (
                f" [FK -> {self._full_table_name(fk.foreign_table, fk.foreign_schema_name)}.{self._quote_column(fk.foreign_columns[0])}]"
                if not is_composite_fk
                else " [FK-composite]"
            )

        if add_description and column.description:
            res += f" /* {column.description} */"
        return res
