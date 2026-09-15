"""Compact text formatting for SQL schemas."""

from dataclasses import dataclass
from typing import ClassVar, Literal

from tabulaflow.core.schema import ForeignKeySchema, SQLColumnSchema, SQLDialect, SQLSchema, SQLTableSchema
from tabulaflow.output.formatting._core import format_single_line_text
from tabulaflow.output.formatting._sql import (
    _PreparedTable,
    SQLQuoting,
    format_column_type,
    format_ratio_as_percent,
    prepare_tables_for_formatting,
)
from tabulaflow.output.formatting.schema import schema_formatter_registry


@schema_formatter_registry.register
@dataclass
class SQLCompactSchemaFormatter:
    """Formats SQL schemas as compact text with inline PK/FK markers."""

    name: ClassVar[str] = "sql_compact"
    schema_kind: ClassVar[Literal["sql"]] = "sql"
    example_max_chars: int = 100
    floatfmt: str = ".8g"
    max_total_columns: int | None = None
    max_native_dtype_chars: int = 80
    compact_table_families: bool = False

    def _format_value(self, value: object, quoting: SQLQuoting) -> str:
        if isinstance(value, str):
            return quoting.quote(self._truncate(value))
        if isinstance(value, float):
            return f"{value:{self.floatfmt}}"
        return str(value)

    def _truncate(self, value: str) -> str:
        value = format_single_line_text(value)
        if len(value) <= self.example_max_chars:
            return value
        return value[: self.example_max_chars // 2] + "..." + value[-self.example_max_chars // 2 :]

    def format(self, schema: SQLSchema, *, include_descriptions: bool = False) -> str:
        quoting = SQLQuoting.from_dialect(schema.dialect)
        result = f"Data source: {schema.display_name}"
        if schema.dialect:
            result += f" (SQL dialect: {schema.dialect})"
        if include_descriptions and schema.description:
            result += f"\nDescription: {schema.description}"
        if not schema.tables:
            return f"{result}\n(no tables)"

        tables = [
            self._format_prepared_table(
                prepared,
                quoting=quoting,
                include_descriptions=include_descriptions,
            )
            for prepared in prepare_tables_for_formatting(
                schema,
                compact_table_families=self.compact_table_families,
                max_total_columns=self.max_total_columns,
            )
        ]
        return result + "\n\n" + "\n\n".join(tables)

    def format_table(
        self,
        table: SQLTableSchema,
        *,
        dialect: SQLDialect | None,
        include_descriptions: bool = False,
    ) -> str:
        return self._format_prepared_table(
            _PreparedTable.from_table(table),
            quoting=SQLQuoting.from_dialect(dialect),
            include_descriptions=include_descriptions,
        )

    def _format_prepared_table(
        self,
        prepared: _PreparedTable,
        *,
        quoting: SQLQuoting,
        include_descriptions: bool,
    ) -> str:
        table = prepared.render_table
        group = prepared.group
        title = f"(SCHEMA: {quoting.quote_if_needed(table.schema_name)})"
        metadata: list[str] = []
        if group.is_family:
            title += f" TABLE FAMILY: {quoting.quote_if_needed(group.display_name)}"
            metadata.extend(
                [
                    str(group.member_summary),
                    "",
                    f"Representative table: {quoting.quote_if_needed(group.representative.name)}",
                    "The schema, row count, descriptions, and column profiles below come from this physical table.",
                ]
            )
        else:
            title += f" TABLE: {quoting.quote_if_needed(table.name)}"

        if table.num_rows is not None:
            metadata.append(f"Rows: {table.num_rows}")
        if include_descriptions and table.description:
            metadata.append(f"Description: {table.description}")

        result = f"=== {title} ===\n"
        if metadata:
            result += "\n".join(metadata) + "\n"

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
        if prepared.omitted_column_count:
            column_lines.append(f"  ... {prepared.omitted_column_count} more columns omitted")
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
        result = f"- {quoting.quote_column(column.name)}: {format_column_type(column, self.max_native_dtype_chars)}"
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
