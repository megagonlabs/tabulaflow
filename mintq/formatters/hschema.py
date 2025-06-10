import collections
from typing import ClassVar
from dataclasses import dataclass
from mintq.schema import HSQLSchema, HTableSchema, HColumnGroup, HTableSection, HTableGroup


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


@dataclass
class HSchemaFormatter:
    name: ClassVar[str] = "hschema"
    quote_char: str = '"'
    example_max_chars: int = 100

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

    def format(self, schema: HSQLSchema) -> str:
        return f"Database: {schema.name}\n\n" + "\n\n".join([self.format_table_group(tg) for tg in schema.table_groups])

    def format_table_group(self, tg: HTableGroup) -> str:
        return (
            f"=== TABLE: {self._full_table_name(tg.name, tg.tables[0].schema_name)} ===\n"
            + "\n\n".join([self.format_section(section, tg.tables[0]) for section in tg.tables[0].sections])
            + "\n=== END OF TABLE ==="
        )

    def format_section(self, section: HTableSection, table: HTableSchema) -> str:
        res = f"[{section.name}] ({section.description})\n"
        res += "\n".join([self.format_column_group(column_group) for column_group in section.column_groups])
        return res

    def format_column_group(self, column_group: HColumnGroup) -> str:
        sample_col = column_group.columns[0]
        if column_group.description:
            desc = f" ({column_group.description})"
        else:
            desc = ""
        res = f"- {self._quote_if_needed(column_group.name)}{desc}: {sample_col.dtype}"
        is_categorical = (
            sample_col.dtype in ("TEXT", "VARCHAR")
            and 0 < sample_col.num_unique <= 20
            and sample_col.unique_ratio < 0.01
        )
        if is_categorical:
            valid_values = [self._quote(self._truncate(v)) for v in sample_col.examples]
            valid_values = sorted(valid_values)
            res += " {" + ", ".join(valid_values) + "}"
        elif not sample_col.examples:
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
