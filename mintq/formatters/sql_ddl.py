from typing import ClassVar
from dataclasses import dataclass
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema
from mintq.formatters.base import formatter_registry


@formatter_registry.register
@dataclass
class SQLDDLSchemaFormatter:
    """Formats schema as DDL statements with additional info like descriptions using comments."""

    name: ClassVar[str] = "sql_ddl"
    quote_char: str = '"'
    include_examples: bool = True
    example_max_chars: int = 100

    def _quote(self, s: str) -> str:
        return f"{self.quote_char}{s}{self.quote_char}"

    def _quote_if_needed(self, s: str | None) -> str:
        if s is None:
            return "NULL"
        # Quote if contains spaces, special chars, or is a reserved word
        if " " in s or "-" in s or not s.isidentifier():
            return self._quote(s)
        return s

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

    def _map_dtype_to_sql(self, dtype: str) -> str:
        """Map internal dtype to SQL DDL type."""
        # Already in SQL format, return as-is
        return dtype

    def format(self, schema: SQLSchema, pk_fk_column_only: bool = False, add_description: bool = False) -> str:
        lines = [f"-- Database: {schema.name}"]
        if not schema.tables:
            lines.append("-- (database has no tables)")
            return "\n".join(lines)

        for table in schema.tables:
            lines.append("")  # Blank line between tables
            lines.append(self.format_table(table, pk_fk_column_only, add_description))

        return "```sql\n" + "\n".join(lines) + "\n```"

    def format_table(
        self, table: SQLTableSchema, pk_fk_column_only: bool = False, add_description: bool = False
    ) -> str:
        lines = []

        # Table header comment
        table_name = self.format_table_name(table)
        header_comment = f"-- Table: {table_name}"
        if table.num_rows is not None:
            header_comment += f" ({table.num_rows} rows)"
        lines.append(header_comment)

        # Table description
        if add_description and table.description:
            lines.append(f"-- Description: {table.description}")
        if table.name_description:
            lines.append(f"-- Note: {table.name_description}")

        # CREATE TABLE statement
        create_stmt = f"CREATE TABLE {table_name} ("

        # Filter columns if pk_fk_column_only
        columns = [col for col in table.columns if not pk_fk_column_only or col.primary_key_type or col.foreign_keys]

        # Format columns
        column_defs = []
        for column in columns:
            column_defs.append(self.format_column(column, add_description))

        # Add composite primary key constraint if needed
        composite_pk_cols = [col.name for col in table.columns if col.primary_key_type == "composite"]
        if composite_pk_cols:
            pk_cols_str = ", ".join(self._quote_if_needed(c) for c in composite_pk_cols)
            column_defs.append(f"    PRIMARY KEY ({pk_cols_str})")

        # Add foreign key constraints
        for fk in table.foreign_keys:
            fk_cols = ", ".join(self._quote_if_needed(c) for c in fk.columns)
            ref_table = self._full_table_name(fk.foreign_table, fk.foreign_schema_name)
            ref_cols = ", ".join(self._quote_if_needed(c) for c in fk.foreign_columns)
            column_defs.append(f"    FOREIGN KEY ({fk_cols}) REFERENCES {ref_table}({ref_cols})")

        lines.append(create_stmt)

        # Join column definitions with commas placed before comments (not after)
        formatted_defs = []
        for i, col_def in enumerate(column_defs):
            if i < len(column_defs) - 1:  # Not the last definition
                if "  -- " in col_def:
                    # Insert comma before the comment
                    col_def = col_def.replace("  -- ", ",  -- ", 1)
                else:
                    col_def += ","
            formatted_defs.append(col_def)
        lines.append("\n".join(formatted_defs))
        lines.append(");")

        return "\n".join(lines)

    def format_column(self, column: SQLColumnSchema, add_description: bool = False) -> str:
        parts = []

        # Column name and type
        col_name = self._quote_if_needed(column.name)
        col_type = self._map_dtype_to_sql(column.dtype)
        parts.append(f"    {col_name} {col_type}")

        # NULL / NOT NULL constraint
        if not column.nullable and column.null_ratio < 1.0:
            parts.append("NOT NULL")
        elif column.nullable:
            parts.append("NULL")

        # Single primary key constraint (inline)
        if column.primary_key_type == "single":
            parts.append("PRIMARY KEY")

        # Build the column definition
        col_def = " ".join(parts)

        # Add inline comment with description and examples
        comments = []

        if add_description and column.description:
            comments.append(column.description)

        # Add example values as comment
        if self.include_examples and column.examples:
            is_categorical = (
                column.dtype in ("TEXT", "VARCHAR", "ENUM")
                and column.num_unique
                and column.unique_ratio
                and (0 < column.num_unique <= 10 or (0 < column.num_unique <= 20 and column.unique_ratio < 0.01))
            )
            if is_categorical:
                valid_values = [f"'{self._truncate(v)}'" for v in column.examples]
                valid_values = sorted(valid_values)
                comments.append(f"values: {{{', '.join(valid_values)}}}")
            else:
                example = column.examples[0]
                if isinstance(example, str):
                    example = f"'{self._truncate(example)}'"
                elif isinstance(example, float):
                    example = f"{example:.3f}"
                else:
                    example = str(example)
                comments.append(f"e.g. {example}")

        # Add FK reference info as comment
        for fk in column.foreign_keys:
            if len(fk.columns) == 1:  # Single column FK
                ref_table = self._full_table_name(fk.foreign_table, fk.foreign_schema_name)
                ref_col = self._quote_if_needed(fk.foreign_columns[0])
                comments.append(f"FK -> {ref_table}.{ref_col}")
            else:
                comments.append("FK (composite)")

        if comments:
            col_def += "  -- " + "; ".join(comments)

        return col_def
