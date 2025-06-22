from typing import ClassVar
from dataclasses import dataclass
from mintq.schema import HSQLSchema, HColumnGroup, HTableSection, HTableGroup


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

    def _quote_if_needed(self, s: str | None) -> str:
        if s is None:
            return "NULL"
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

    def format(self, schema: HSQLSchema) -> str:
        if not schema.table_groups:
            return f"Database: {schema.name}\n(database has no tables)"
        return f"Database: {schema.name}\n\n" + "\n\n".join([self.format_table_group(tg) for tg in schema.table_groups])

    def format_table_group(self, tg: HTableGroup) -> str:
        return (
            f"=== (SCHEMA: {self._quote_if_needed(tg.schema_name)}) TABLE: {self._quote_if_needed(tg.name)} ===\n"
            + "\n\n".join([self.format_section(section) for section in tg.sections])
            + "\n=== END OF TABLE ==="
        )

    def format_section(self, section: HTableSection) -> str:
        res = f"[{section.name}] ({section.description})\n"
        res += "\n".join([self.format_column_group(column_group) for column_group in section.column_groups])
        return res

    def format_column_group(self, column_group: HColumnGroup) -> str:
        if column_group.description:
            desc = f" ({column_group.description})"
        else:
            desc = ""
        res = f"- {self._quote_if_needed(column_group.name)}{desc}: {column_group.dtype}"
        is_categorical = (
            column_group.dtype in ("TEXT", "VARCHAR")
            and column_group.num_unique
            and column_group.unique_ratio
            and 0 < column_group.num_unique <= 20
            and column_group.unique_ratio < 0.01
        )
        if is_categorical:
            valid_values = [self._quote(self._truncate(v)) for v in column_group.examples]
            valid_values = sorted(valid_values)
            res += " {" + ", ".join(valid_values) + "}"
        elif not column_group.examples:
            res += " (all values are null)"
        else:
            example = column_group.examples[0]
            if isinstance(example, str):
                example = self._quote(example)
            elif isinstance(example, float):
                example = f"{example:.3f}"
            else:
                example = str(example)
            example = self._truncate(example)
            res += f" (e.g. {example})"
        return res
