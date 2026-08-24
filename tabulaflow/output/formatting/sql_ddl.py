"""Annotated DDL formatting for SQL schemas."""

from typing import ClassVar
from dataclasses import dataclass
from tabulaflow.core.schema import ForeignKeySchema, SQLColumnSchema, SQLDialect, SQLSchema, SQLTableSchema
from tabulaflow.output.formatting.schema import schema_formatter_registry
from tabulaflow.output.formatting._core import (
    format_dataframe,
    format_json_schema_type,
    format_single_line_text,
)
from tabulaflow.output.formatting._sql import (
    _PreparedTable,
    SQLQuoting,
    format_ratio_as_percent,
    format_column_type,
    prepare_tables_for_formatting,
)


@schema_formatter_registry.register
@dataclass
class SQLDDLSchemaFormatter:
    """Formats SQL schemas as annotated DDL with complete table-level constraints."""

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
    compact_table_families: bool = False
    """When ``column.native_dtype`` is set and its length is within this cap,
    emit it as the DDL column type instead of the canonical ``dtype`` token.
    For long composite types, the structural info is conveyed via the
    ``<json_schema>`` comment instead."""

    def _truncate(self, s: str) -> str:
        s = format_single_line_text(s)
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
        return format_column_type(column, self.max_native_dtype_chars)

    def _format_sampled_df(self, table: SQLTableSchema) -> str:
        """Format a DataFrame as a markdown table (without wrapper)."""
        df = table.sampled_df.head(5)  # type: ignore
        has_more_rows = len(table.sampled_df) > len(df) or table.num_rows is None or table.num_rows > len(df)  # type: ignore
        md_table = format_dataframe(df, max_visible_rows=5, add_bottom_ellipsis_row=has_more_rows)
        return f"Sample rows:\n{md_table}"

    def format(self, schema: SQLSchema, *, include_descriptions: bool = False) -> str:
        quoting = SQLQuoting.from_dialect(schema.dialect)
        name_label = "Project" if schema.dialect == "bigquery" else "Database"
        metadata_lines = [f"**{name_label}:** `{schema.name}`"]
        if schema.dialect:
            metadata_lines.append(f"**SQL Dialect:** `{schema.dialect}`")
        if include_descriptions and schema.description:
            metadata_lines.append("**Description:**")
            metadata_lines.append(f"```text\n{schema.description}\n```")
        if not schema.tables:
            metadata_lines.append("_(database has no tables)_")
            return "\n".join(metadata_lines)

        prepared_tables = prepare_tables_for_formatting(
            schema,
            compact_table_families=self.compact_table_families,
            max_total_columns=self.max_total_columns,
        )
        lines: list[str] = []
        include_sampled_rows = self.include_sampled_df and len(prepared_tables) <= self.include_sampled_df_max_tables
        for prepared in prepared_tables:
            if lines:
                lines.append("")
            lines.append(
                self._format_prepared_table(
                    prepared,
                    quoting=quoting,
                    include_descriptions=include_descriptions,
                    include_sampled_rows=include_sampled_rows,
                )
            )

        sql_block = "```sql\n" + "\n".join(lines) + "\n```"
        return "\n".join(metadata_lines) + "\n\n" + sql_block

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
            include_sampled_rows=self.include_sampled_df,
        )

    def _format_prepared_table(
        self,
        prepared: _PreparedTable,
        *,
        quoting: SQLQuoting,
        include_descriptions: bool,
        include_sampled_rows: bool,
    ) -> str:
        table = prepared.render_table
        group = prepared.group
        lines = []

        # Build table info block content
        table_name = quoting.qualified_table(table.name, table.schema_name)
        info_parts = [f"Schema: {quoting.quote_if_needed(table.schema_name)}"]
        if group.is_family:
            info_parts.extend(
                [
                    f"Table family: {quoting.quote_if_needed(group.display_name)}",
                    str(group.member_summary),
                    "",
                    f"Representative table: {quoting.quote_if_needed(group.representative.name)}",
                    "The schema, row count, descriptions, column profiles, and samples below come from this physical table.",
                ]
            )
        else:
            info_parts.append(f"Table: {quoting.quote_if_needed(table.name)}")

        if table.num_rows is not None:
            info_parts.append(f"Rows: {table.num_rows}")
        if include_descriptions and table.description:
            info_parts.append(f"Description: {table.description}")

        # Add sampled rows to info block
        if (
            include_sampled_rows
            and len(table.columns) <= self.include_sampled_df_max_columns
            and table.sampled_df is not None
            and not table.sampled_df.empty
        ):
            info_parts.append(self._format_sampled_df(table))

        # Format as single /* */ block
        lines.append("/*\n" + "\n".join(info_parts) + "\n*/")

        kind = "VIEW" if table.is_view else "TABLE"
        create_stmt = f"CREATE {kind} {table_name} ("

        primary_key_names = set(table.primary_key)
        foreign_keys_by_column: dict[str, list[ForeignKeySchema]] = {column.name: [] for column in table.columns}
        for foreign_key in table.foreign_keys:
            for column_name in foreign_key.columns:
                if column_name in foreign_keys_by_column:
                    foreign_keys_by_column[column_name].append(foreign_key)

        column_defs = [
            self._format_column(
                column,
                quoting=quoting,
                include_description=include_descriptions,
                is_single_primary_key=len(primary_key_names) == 1 and column.name in primary_key_names,
                foreign_keys=foreign_keys_by_column[column.name],
            )
            for column in table.columns
        ]

        if prepared.omitted_column_count > 0:
            column_defs.append(f"    -- ... {prepared.omitted_column_count} more columns omitted")

        # Add composite primary key constraint if needed
        if len(primary_key_names) > 1:
            pk_cols_str = ", ".join(quoting.quote_column(name) for name in table.primary_key)
            column_defs.append(f"    PRIMARY KEY ({pk_cols_str})")

        # Add foreign key constraints
        for fk in table.foreign_keys:
            fk_cols = ", ".join(quoting.quote_column(name) for name in fk.columns)
            ref_table = quoting.qualified_table(fk.foreign_table, fk.foreign_schema_name)
            ref_cols = ", ".join(quoting.quote_column(name) for name in fk.foreign_columns)
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

    def _format_column(
        self,
        column: SQLColumnSchema,
        *,
        quoting: SQLQuoting,
        include_description: bool,
        is_single_primary_key: bool,
        foreign_keys: list[ForeignKeySchema],
    ) -> str:
        parts = []

        # Column name and type
        col_name = quoting.quote_column(column.name)
        col_type = self._map_dtype_to_sql(column)
        parts.append(f"    {col_name} {col_type}")

        # NULL / NOT NULL constraint
        if not column.nullable:
            parts.append("NOT NULL")
        else:
            parts.append("NULL")

        # Single primary key constraint (inline)
        if is_single_primary_key:
            parts.append("PRIMARY KEY")

        # Build the column definition
        col_def = " ".join(parts)

        # Build comment lines with tags, each on a separate line
        comment_lines = []

        if include_description and column.description:
            comment_lines.append(f"        -- <description>{column.description}</description>")

        # Add null ratio for nullable columns
        if self.include_null_ratio and column.nullable and column.null_ratio is not None:
            comment_lines.append(f"        -- <null_ratio>{format_ratio_as_percent(column.null_ratio)}</null_ratio>")

        # Add JSON schema for semi-structured columns
        if self.include_json_schema and column.json_schema:
            formatted = format_json_schema_type(column.json_schema, max_fields=self.include_json_schema_max_fields)
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
        for fk in foreign_keys:
            if len(fk.columns) == 1:  # Single column FK
                ref_table = quoting.qualified_table(fk.foreign_table, fk.foreign_schema_name)
                ref_col = quoting.quote_column(fk.foreign_columns[0])
                comment_lines.append(f"        -- <fk> -> {ref_table}.{ref_col}</fk>")
            else:
                comment_lines.append("        -- <fk>composite</fk>")

        if comment_lines:
            col_def += "\n" + "\n".join(comment_lines)

        return col_def
