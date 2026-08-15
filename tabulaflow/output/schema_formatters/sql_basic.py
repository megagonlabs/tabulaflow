from dataclasses import dataclass
from typing import ClassVar

from tabulaflow.core import ForeignKeySchema, SQLColumnSchema, SQLDialect, SQLSchema, SQLTableSchema
from tabulaflow.output.formatting import flatten_multiline, format_ratio_as_percent, render_column_dtype
from tabulaflow.output.schema_formatters._sql_quoting import SQLQuoting
from tabulaflow.output.schema_formatters._sql_selection import select_tables_for_formatting
from tabulaflow.output.schema_formatters.base import schema_formatter_registry


@schema_formatter_registry.register
@dataclass
class SQLBasicSchemaFormatter:
    """Formats SQL schemas as compact text with inline PK/FK markers."""

    name: ClassVar[str] = "sql_basic"
    example_max_chars: int = 100
    floatfmt: str = ".8g"
    max_total_columns: int | None = None
    max_native_dtype_chars: int = 80

    def _format_value(self, value: object, quoting: SQLQuoting) -> str:
        if isinstance(value, str):
            return quoting.quote(self._truncate(value))
        if isinstance(value, float):
            return f"{value:{self.floatfmt}}"
        return str(value)

    def _truncate(self, value: str) -> str:
        value = flatten_multiline(value)
        if len(value) <= self.example_max_chars:
            return value
        return value[: self.example_max_chars // 2] + "..." + value[-self.example_max_chars // 2 :]

    def format(self, schema: SQLSchema, *, include_descriptions: bool = False) -> str:
        quoting = SQLQuoting.from_dialect(schema.dialect)
        name_label = "Project" if schema.dialect == "bigquery" else "Database"
        result = f"{name_label}: {schema.name}"
        if schema.dialect:
            result += f" (SQL Dialect: {schema.dialect})"
        if include_descriptions and schema.description:
            result += f"\nDescription: {schema.description}"
        if not schema.tables:
            return f"{result}\n(database has no tables)"

        tables = [
            self._format_table(
                table,
                quoting=quoting,
                include_descriptions=include_descriptions,
                omitted_column_count=omitted_column_count,
            )
            for table, omitted_column_count in select_tables_for_formatting(schema, self.max_total_columns)
        ]
        return result + "\n\n" + "\n\n".join(tables)

    def format_table(
        self,
        table: SQLTableSchema,
        *,
        dialect: SQLDialect | None,
        include_descriptions: bool = False,
    ) -> str:
        return self._format_table(
            table,
            quoting=SQLQuoting.from_dialect(dialect),
            include_descriptions=include_descriptions,
        )

    def _format_table(
        self,
        table: SQLTableSchema,
        *,
        quoting: SQLQuoting,
        include_descriptions: bool,
        omitted_column_count: int = 0,
    ) -> str:
        result = f"(SCHEMA: {quoting.quote_if_needed(table.schema_name)}) TABLE:"
        if table.name_patterns:
            patterns = []
            for pattern in table.name_patterns:
                formatted = quoting.quote_if_needed(pattern.pattern)
                if pattern.comment:
                    formatted += f" ({pattern.comment})"
                patterns.append(formatted)
            result += " " + ", ".join(patterns)
        else:
            result += f" {quoting.quote_if_needed(table.name)}"
        if table.num_rows is not None:
            result += f" ({table.num_rows} rows)"
        if include_descriptions and table.description:
            result += f" -- {table.description}"
        result = f"=== {result} ===\n"

        composite_foreign_keys = []
        for foreign_key in table.foreign_keys:
            if len(foreign_key.columns) > 1:
                local_columns = "(" + ", ".join(quoting.quote_column(name) for name in foreign_key.columns) + ")"
                foreign_table = quoting.qualified_table(foreign_key.foreign_table, foreign_key.foreign_schema_name)
                foreign_columns = (
                    "(" + ", ".join(quoting.quote_column(name) for name in foreign_key.foreign_columns) + ")"
                )
                composite_foreign_keys.append(f"* {local_columns} -> {foreign_table}.{foreign_columns}")
        if composite_foreign_keys:
            result += "[Composite FKs]\n" + "\n".join(composite_foreign_keys) + "\n\n"

        primary_key_names = set(table.primary_key)
        primary_key_kind = "single" if len(primary_key_names) == 1 else "composite"
        foreign_keys_by_column: dict[str, list[ForeignKeySchema]] = {column.name: [] for column in table.columns}
        for foreign_key in table.foreign_keys:
            for column_name in foreign_key.columns:
                if column_name in foreign_keys_by_column:
                    foreign_keys_by_column[column_name].append(foreign_key)

        column_lines = [
            self._format_column(
                column,
                quoting=quoting,
                include_description=include_descriptions,
                primary_key_kind=primary_key_kind if column.name in primary_key_names else None,
                foreign_keys=foreign_keys_by_column[column.name],
            )
            for column in table.columns
        ]
        if omitted_column_count:
            column_lines.append(f"  ... {omitted_column_count} more columns omitted")
        result += "\n".join(column_lines)
        return result + "\n=== END OF TABLE ==="

    def _format_column(
        self,
        column: SQLColumnSchema,
        *,
        quoting: SQLQuoting,
        include_description: bool,
        primary_key_kind: str | None,
        foreign_keys: list[ForeignKeySchema],
    ) -> str:
        result = f"- {quoting.quote_column(column.name)}: {render_column_dtype(column, self.max_native_dtype_chars)}"
        if column.nullable:
            if column.null_ratio == 1.0:
                result += " (all values are null)"
            else:
                result += " NULLABLE"
                if column.null_ratio is not None:
                    result += f" (null_ratio={format_ratio_as_percent(column.null_ratio)})"

        is_categorical = (
            column.dtype in ("TEXT", "VARCHAR", "STRING", "ENUM")
            and column.num_unique is not None
            and column.unique_ratio is not None
            and (0 < column.num_unique <= 10 or (0 < column.num_unique <= 20 and column.unique_ratio < 0.01))
        )
        if is_categorical:
            values = sorted(self._format_value(value, quoting) for value in column.examples)
            result += " {" + ", ".join(values) + "}"
        elif column.examples:
            result += f" (e.g. {self._format_value(column.examples[0], quoting)})"

        if primary_key_kind:
            result += " [PK]" if primary_key_kind == "single" else " [PK-composite]"
        for foreign_key in foreign_keys:
            if len(foreign_key.columns) == 1:
                foreign_table = quoting.qualified_table(foreign_key.foreign_table, foreign_key.foreign_schema_name)
                referenced_column = quoting.quote_column(foreign_key.foreign_columns[0])
                result += f" [FK -> {foreign_table}.{referenced_column}]"
            else:
                result += " [FK-composite]"

        if include_description and column.description:
            result += f" /* {column.description} */"
        return result
