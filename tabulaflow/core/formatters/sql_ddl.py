from typing import ClassVar
from dataclasses import dataclass, field
from tabulaflow.schema import SQLDialect, SQLSchema, SQLTableSchema, SQLColumnSchema
from tabulaflow.core.formatters.base import formatter_registry
from tabulaflow.core.utils import format_df, flatten_multiline, format_json_schema, format_ratio_as_percent, render_column_dtype

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


@formatter_registry.register
@dataclass
class SQLDDLSchemaFormatter:
    """Formats schema as DDL statements with additional info like descriptions using comments."""

    name: ClassVar[str] = "sql_ddl"
    include_examples: bool = True
    include_sampled_df: bool = True
    include_sampled_df_max_columns: int = 10
    include_sampled_df_max_tables: int = 20
    example_max_chars: int = 100
    floatfmt: str = ".8g"
    max_total_columns: int | None = None
    include_null_ratio: bool = True
    include_json_schema: bool = True
    include_json_schema_max_fields: int | None = 20
    max_native_dtype_chars: int = 80
    """When ``column.native_dtype`` is set and its length is within this cap,
    emit it as the DDL column type instead of the canonical ``dtype`` token.
    For long composite types, the structural info is conveyed via the
    ``<json_schema>`` comment instead."""

    _quote_char: str = field(default='"', init=False, repr=False)
    _always_quote_columns: bool = field(default=True, init=False, repr=False)

    def set_dialect(self, dialect: SQLDialect | None) -> None:
        """Configure quoting for a SQL dialect."""
        self._quote_char, self._always_quote_columns = _DIALECT_QUOTING.get(dialect or "", _DEFAULT_QUOTING)

    def _quote(self, s: str) -> str:
        return f"{self._quote_char}{s}{self._quote_char}"

    def _quote_if_needed(self, s: str | None) -> str:
        if s is None:
            return "NULL"
        if " " in s or "-" in s or not s.isidentifier():
            return self._quote(s)
        return s

    def _quote_column(self, s: str) -> str:
        if self._always_quote_columns:
            return self._quote(s)
        return self._quote_if_needed(s)

    def _full_table_name(self, table: str, schema: str | None) -> str:
        if schema is None:
            return self._quote_if_needed(table)
        else:
            return f"{self._quote_if_needed(schema)}.{self._quote_if_needed(table)}"

    def format_table_name(self, table: SQLTableSchema) -> str:
        return self._full_table_name(table.name, table.schema_name)

    def _truncate(self, s: str) -> str:
        s = flatten_multiline(s)
        if len(s) <= self.example_max_chars:
            return s
        return s[: self.example_max_chars // 2] + "..." + s[-self.example_max_chars // 2 :]

    def format_value(self, value: object) -> str:
        """Format a single value for display in comments."""
        if isinstance(value, str):
            return f"'{self._truncate(value)}'"
        elif isinstance(value, float):
            return f"{value:{self.floatfmt}}"
        else:
            return str(value)

    def _map_dtype_to_sql(self, column: SQLColumnSchema) -> str:
        """Render a column's type for emission in DDL."""
        return render_column_dtype(column, self.max_native_dtype_chars)

    def _format_sampled_df(self, table: SQLTableSchema) -> str:
        """Format a DataFrame as a markdown table (without wrapper)."""
        if table.num_rows is not None and table.num_rows <= 10:
            md_table = format_df(table.sampled_df, max_visible_rows=len(table.sampled_df))  # type: ignore
            return f"All rows:\n{md_table}"
        else:
            df = table.sampled_df.head(5)  # type: ignore
            md_table = format_df(df, max_visible_rows=5, add_bottom_ellipsis_row=True)
            return f"Sample rows:\n{md_table}"

    def _compute_column_quotas(self, tables: list[SQLTableSchema]) -> list[int | None]:
        """Compute equal per-table column quotas from max_total_columns."""
        if self.max_total_columns is None:
            return [None] * len(tables)
        if not tables:
            return []
        quota = max(1, self.max_total_columns // len(tables))
        return [quota] * len(tables)

    def format(self, schema: SQLSchema, pk_fk_column_only: bool = False, add_description: bool = False) -> str:
        self.set_dialect(schema.dialect)
        name_label = "Project" if schema.dialect == "bigquery" else "Database"
        metadata_lines = [f"**{name_label}:** `{schema.name}`"]
        if schema.dialect:
            metadata_lines.append(f"**SQL Dialect:** `{schema.dialect}`")
        if schema.description:
            metadata_lines.append("**Description:**")
            metadata_lines.append(f"```text\n{schema.description}\n```")
        if not schema.tables:
            metadata_lines.append("_(database has no tables)_")
            return "\n".join(metadata_lines)

        lines: list[str] = []
        quotas = self._compute_column_quotas(schema.tables)
        for table, max_columns in zip(schema.tables, quotas):
            lines.append("")  # Blank line between tables
            lines.append(
                self.format_table(
                    table,
                    pk_fk_column_only,
                    add_description,
                    max_columns=max_columns,
                    num_tables=len(schema.tables),
                )
            )

        sql_block = "```sql\n" + "\n".join(lines) + "\n```"
        return "\n".join(metadata_lines) + "\n\n" + sql_block

    def format_table(
        self,
        table: SQLTableSchema,
        pk_fk_column_only: bool = False,
        add_description: bool = False,
        max_columns: int | None = None,
        num_tables: int | None = None,
    ) -> str:
        lines = []

        # Build table info block content
        table_name = self.format_table_name(table)
        title = ""
        title += f"Schema: {self._quote_if_needed(table.schema_name)}"
        title += "\nTable:"
        if table.name_patterns:  # This is a compressed table
            for pattern in table.name_patterns:
                title += f"\n  - {self._quote_if_needed(pattern.pattern)}"
                if pattern.comment:
                    title += f" ({pattern.comment})"
        else:
            title += f" {self._quote_if_needed(table.name)}"
        info_parts = [title]
        if table.num_rows is not None:
            info_parts.append(f"Rows: {table.num_rows}")
        if add_description and table.description:
            info_parts.append(f"Description: {table.description}")

        # Add sampled rows to info block
        if (
            self.include_sampled_df
            and len(table.columns) <= self.include_sampled_df_max_columns
            and (num_tables is None or num_tables <= self.include_sampled_df_max_tables)
            and table.sampled_df is not None
            and not table.sampled_df.empty
        ):
            info_parts.append(self._format_sampled_df(table))

        # Format as single /* */ block
        lines.append("/*\n" + "\n".join(info_parts) + "\n*/")

        kind = "VIEW" if table.is_view else "TABLE"
        create_stmt = f"CREATE {kind} {table_name} ("

        # Filter columns if pk_fk_column_only
        columns = [col for col in table.columns if not pk_fk_column_only or col.primary_key_type or col.foreign_keys]

        # Truncate columns if max_columns is set
        omitted_count = 0
        if max_columns is not None and len(columns) > max_columns:
            omitted_count = len(columns) - max_columns
            columns = columns[:max_columns]

        # Format columns
        column_defs = []
        for column in columns:
            column_defs.append(self.format_column(column, add_description))

        if omitted_count > 0:
            column_defs.append(f"    -- ... {omitted_count} more columns omitted")

        # Add composite primary key constraint if needed
        composite_pk_cols = [col.name for col in table.columns if col.primary_key_type == "composite"]
        if composite_pk_cols:
            pk_cols_str = ", ".join(self._quote_column(c) for c in composite_pk_cols)
            column_defs.append(f"    PRIMARY KEY ({pk_cols_str})")

        # Add foreign key constraints
        for fk in table.foreign_keys:
            fk_cols = ", ".join(self._quote_column(c) for c in fk.columns)
            ref_table = self._full_table_name(fk.foreign_table, fk.foreign_schema_name)
            ref_cols = ", ".join(self._quote_column(c) for c in fk.foreign_columns)
            column_defs.append(f"    FOREIGN KEY ({fk_cols}) REFERENCES {ref_table}({ref_cols})")

        lines.append(create_stmt)

        # Join column definitions with commas at the end of the definition line
        formatted_defs = []
        for i, col_def in enumerate(column_defs):
            if i < len(column_defs) - 1:  # Not the last definition
                # Comments are now on separate lines, so add comma at end of first line
                if "\n" in col_def:
                    first_line, rest = col_def.split("\n", 1)
                    col_def = first_line + ",\n" + rest
                else:
                    col_def += ","
            formatted_defs.append(col_def)
        lines.append("\n".join(formatted_defs))
        lines.append(");")

        return "\n".join(lines)

    def format_column(self, column: SQLColumnSchema, add_description: bool = False) -> str:
        parts = []

        # Column name and type
        col_name = self._quote_column(column.name)
        col_type = self._map_dtype_to_sql(column)
        parts.append(f"    {col_name} {col_type}")

        # NULL / NOT NULL constraint
        if not column.nullable:
            parts.append("NOT NULL")
        else:
            parts.append("NULL")

        # Single primary key constraint (inline)
        if column.primary_key_type == "single":
            parts.append("PRIMARY KEY")

        # Build the column definition
        col_def = " ".join(parts)

        # Build comment lines with tags, each on a separate line
        comment_lines = []

        if add_description and column.description:
            comment_lines.append(f"        -- <description>{column.description}</description>")

        # Add null ratio for nullable columns
        if self.include_null_ratio and column.nullable and column.null_ratio is not None:
            comment_lines.append(f"        -- <null_ratio>{format_ratio_as_percent(column.null_ratio)}</null_ratio>")

        # Add JSON schema for semi-structured columns
        if self.include_json_schema and column.json_schema:
            formatted = format_json_schema(column.json_schema, max_fields=self.include_json_schema_max_fields)
            comment_lines.append(f"        -- <json_schema>{formatted}</json_schema>")

        # Add example values as comment
        if self.include_examples and column.examples:
            is_categorical = (
                column.dtype in ("TEXT", "VARCHAR", "STRING", "ENUM")
                and column.num_unique is not None
                and column.unique_ratio is not None
                and (0 < column.num_unique <= 10 or (0 < column.num_unique <= 20 and column.unique_ratio < 0.01))
            )
            if is_categorical:
                valid_values = sorted(self.format_value(v) for v in column.examples)
                comment_lines.append(f"        -- <values>{{{', '.join(valid_values)}}}</values>")
            else:
                comment_lines.append(f"        -- <example>{self.format_value(column.examples[0])}</example>")

        # Add FK reference info as comment
        for fk in column.foreign_keys:
            if len(fk.columns) == 1:  # Single column FK
                ref_table = self._full_table_name(fk.foreign_table, fk.foreign_schema_name)
                ref_col = self._quote_column(fk.foreign_columns[0])
                comment_lines.append(f"        -- <fk> -> {ref_table}.{ref_col}</fk>")
            else:
                comment_lines.append("        -- <fk>composite</fk>")

        if comment_lines:
            col_def += "\n" + "\n".join(comment_lines)

        return col_def
