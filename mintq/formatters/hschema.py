import collections
from mintq.schema import HSQLSchema, HTableSchema, HColumnGroup, HTableSection


"""
DATABASE: european_football_2
* team (Table)
  - id: INTEGER [PK]
  - player1_id: INTEGER [FK -> player.id]
  - ...
* player (Table)
  - id: INTEGER [PK]
  - ...

=== TABLE: team ===
[General]
- id: INTEGER [PK]
- player1_id: INTEGER [FK -> player.id]

[Location]
- city: TEXT (Example: "London")
...

[History]
- founded_at: INTEGER
- dissolved_at: INTEGER
...
=== END OF TABLE ===
"""


class HSchemaFormatter:
    name = "hschema"

    def __init__(self, quote_char: str = '"', example_max_chars: int = 100):
        self.quote_char = quote_char
        self.example_max_chars = example_max_chars

    def _quote(self, s: str) -> str:
        return f"{self.quote_char}{s}{self.quote_char}"

    def _quote_if_needed(self, s: str) -> str:
        return self._quote(s) if " " in s else s

    def _full_table_name(self, table: str, schema: str | None) -> str:
        if schema is None:
            return self._quote_if_needed(table)
        else:
            return f"{self._quote_if_needed(schema)}.{self._quote_if_needed(table)}"

    def _truncate(self, s: str) -> str:
        if len(s) <= self.example_max_chars:
            return s
        return s[: self.example_max_chars // 2] + "..." + s[-self.example_max_chars // 2 :]

    def format_table_name(self, table: HTableSchema) -> str:
        return self._full_table_name(table.name, table.schema_name)

    def format(self, schema: HSQLSchema, include_foreign_keys: bool = True, include_table_schemas: bool = True) -> str:
        table_id_to_fks = collections.defaultdict(list)
        for fk in schema.foreign_keys:
            table_id_to_fks[self._full_table_name(fk.table, fk.schema_name)].append(fk)

        res = f"Database: {schema.name}"
        for tg in schema.table_groups:
            table = tg.tables[0]
            table_id = self._full_table_name(table.name, table.schema_name)
            res += f"\n* {table_id} (Table)"
            if table.primary_key:
                res += f"\n  - [PK] {', '.join([self._quote_if_needed(pk) for pk in table.primary_key])}"
            if include_foreign_keys:
                for fk in table_id_to_fks[table_id]:
                    if len(fk.columns) > 1 or len(fk.foreign_columns) > 1:
                        raise ValueError(f"Multiple foreign keys are not supported: {fk}")
                    res += f"\n  - [FK] {fk.columns[0]} -> {self._full_table_name(fk.foreign_table, fk.foreign_schema_name)}.{self._quote_if_needed(fk.foreign_columns[0])}"

        if include_table_schemas:
            res += "\n\n"
            res += "\n\n".join([self.format_table(tg.tables[0]) for tg in schema.table_groups])
        return res

    def format_table(self, table: HTableSchema) -> str:
        return (
            f"=== TABLE: {self.format_table_name(table)} ===\n"
            + "\n\n".join([self.format_section(section) for section in table.sections])
            + "\n=== END OF TABLE ==="
        )

    def format_section(self, section: HTableSection) -> str:
        res = f"[{section.name}]\n"
        res += "\n".join([self.format_column_group(column_group) for column_group in section.column_groups])
        return res

    def format_column_group(self, column_group: HColumnGroup) -> str:
        sample_col = column_group.columns[0]
        res = f"- {self._quote_if_needed(column_group.name)}: {sample_col.dtype}"
        if not sample_col.examples:
            res += " (all values are null)"
        else:
            example = sample_col.examples[0]
            if isinstance(example, str):
                example = self._quote(example)
            elif isinstance(example, float):
                example = f"{example:.3f}"
            else:
                example = str(example)
            example = self._truncate(example)
            res += f" (e.g. {example})"
        return res
