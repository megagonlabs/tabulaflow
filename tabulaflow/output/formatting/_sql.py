"""Shared SQL schema-formatting helpers."""

from dataclasses import dataclass

from tabulaflow.core.schema import SQLColumnSchema, SQLDialect, SQLSchema, SQLTableSchema
from tabulaflow.output.formatting._table_grouping import _TableRenderGroup, group_tables_for_formatting


_DIALECT_QUOTING: dict[str, tuple[str, bool]] = {
    "bigquery": ("`", False),
    "snowflake": ('"', True),
    "sqlite": ('"', False),
    "mysql": ("`", False),
    "athena": ('"', False),
    "clickhouse": ('"', False),
    "tsql": ('"', True),
}
_DEFAULT_QUOTING = ('"', True)


@dataclass(frozen=True)
class SQLQuoting:
    quote_char: str
    always_quote_columns: bool

    @classmethod
    def from_dialect(cls, dialect: SQLDialect | None) -> "SQLQuoting":
        return cls(*_DIALECT_QUOTING.get(dialect or "", _DEFAULT_QUOTING))

    def quote(self, value: str) -> str:
        return f"{self.quote_char}{value}{self.quote_char}"

    def quote_if_needed(self, value: str | None) -> str:
        if value is None:
            return "NULL"
        if " " in value or "-" in value or not value.isidentifier():
            return self.quote(value)
        return value

    def quote_column(self, name: str) -> str:
        return self.quote(name) if self.always_quote_columns else self.quote_if_needed(name)

    def qualified_table(self, table: str, schema: str | None) -> str:
        if schema is None:
            return self.quote_if_needed(table)
        return f"{self.quote_if_needed(schema)}.{self.quote_if_needed(table)}"


def format_column_type(column: SQLColumnSchema, max_native_dtype_chars: int = 80) -> str:
    """Format a column type for schema output."""
    if column.native_dtype and len(column.native_dtype) <= max_native_dtype_chars:
        return column.native_dtype
    return column.dtype


def format_ratio_as_percent(
    ratio: float,
    *,
    decimals: int = 0,
    min_nonzero_percent: float | None = 1.0,
) -> str:
    """Format a ratio in [0, 1] as a percentage string."""
    if ratio <= 0:
        return "0%"
    if min_nonzero_percent is not None and ratio * 100 < min_nonzero_percent:
        return f"less than {min_nonzero_percent:g}%"
    return f"{ratio:.{decimals}%}"


@dataclass(frozen=True)
class _PreparedTable:
    group: _TableRenderGroup
    render_table: SQLTableSchema
    omitted_column_count: int = 0

    @classmethod
    def from_table(cls, table: SQLTableSchema) -> "_PreparedTable":
        return cls(group=_TableRenderGroup.from_table(table), render_table=table)


def prepare_tables_for_formatting(
    schema: SQLSchema,
    *,
    compact_table_families: bool,
    max_total_columns: int | None,
) -> list[_PreparedTable]:
    groups = (
        group_tables_for_formatting(schema)
        if compact_table_families
        else [_TableRenderGroup.from_table(table) for table in schema.tables]
    )
    if max_total_columns is None or not groups:
        return [_PreparedTable(group=group, render_table=group.representative) for group in groups]

    quota = max(1, max_total_columns // len(groups))
    required_by_table: dict[tuple[str | None, str], set[str]] = {
        (table.schema_name, table.name): set(table.primary_key) for table in schema.tables
    }
    for table in schema.tables:
        required_by_table[(table.schema_name, table.name)].update(
            column_name for foreign_key in table.foreign_keys for column_name in foreign_key.columns
        )
        for foreign_key in table.foreign_keys:
            target = (foreign_key.foreign_schema_name, foreign_key.foreign_table)
            if target in required_by_table:
                required_by_table[target].update(foreign_key.foreign_columns)

    selected_tables: list[_PreparedTable] = []
    for group in groups:
        table = group.representative
        if len(table.columns) <= quota:
            selected_tables.append(_PreparedTable(group=group, render_table=table))
            continue

        required = required_by_table[(table.schema_name, table.name)]
        ordinary = [column.name for column in table.columns if column.name not in required]
        selected_names = required | set(ordinary[: max(0, quota - len(required))])
        selected = table.select_columns(list(selected_names), include_primary_key=False)
        omitted_column_count = len(table.columns) - len(selected.columns)
        selected_tables.append(
            _PreparedTable(group=group, render_table=selected, omitted_column_count=omitted_column_count)
        )

    return selected_tables
