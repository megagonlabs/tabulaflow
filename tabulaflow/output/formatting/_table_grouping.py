"""Private table-family grouping for SQL schema rendering."""

from collections import defaultdict
from dataclasses import dataclass
import datetime
import re
from typing import Hashable, Literal

from tabulaflow.core import SQLSchema, SQLTableSchema


_MAX_LISTED_VALUES = 20
_MAX_LISTED_MISSING_VALUES = 10
_MAX_EXAMPLE_VALUES = 10


@dataclass(frozen=True)
class _ParsedTableName:
    pattern: str
    kind: Literal["YYYYMMDD", "YYYYMM", "YEAR", "NUM"]
    value: datetime.date | int
    text: str


@dataclass(frozen=True)
class _TableRenderGroup:
    members: tuple[SQLTableSchema, ...]
    display_name: str
    member_summary: str | None = None

    @classmethod
    def from_table(cls, table: SQLTableSchema) -> "_TableRenderGroup":
        return cls(members=(table,), display_name=table.name)

    @property
    def representative(self) -> SQLTableSchema:
        return self.members[0]

    @property
    def is_family(self) -> bool:
        return len(self.members) > 1


def _replace_match(name: str, match: re.Match[str], placeholder: str) -> str:
    return name[: match.start()] + placeholder + name[match.end() :]


def _parse_name(name: str) -> _ParsedTableName | None:
    for match in re.finditer(r"(?<!\d)\d{8}(?!\d)", name):
        text = match.group()
        try:
            date_value = datetime.date(int(text[:4]), int(text[4:6]), int(text[6:]))
        except ValueError:
            continue
        if date_value.year >= 1000:
            return _ParsedTableName(_replace_match(name, match, "{YYYYMMDD}"), "YYYYMMDD", date_value, text)

    for match in re.finditer(r"(?<!\d)\d{6}(?!\d)", name):
        text = match.group()
        year = int(text[:4])
        month = int(text[4:])
        if year >= 1000 and 1 <= month <= 12:
            return _ParsedTableName(
                _replace_match(name, match, "{YYYYMM}"),
                "YYYYMM",
                datetime.date(year, month, 1),
                text,
            )

    for match in re.finditer(r"(?<!\d)\d{4}(?!\d)", name):
        text = match.group()
        year_value = int(text)
        if year_value >= 1000:
            return _ParsedTableName(_replace_match(name, match, "{YEAR}"), "YEAR", year_value, text)

    numeric_match = re.search(r"\d+", name)
    if numeric_match is not None:
        text = numeric_match.group()
        return _ParsedTableName(_replace_match(name, numeric_match, "{NUM}"), "NUM", int(text), text)
    return None


def _foreign_key_signature(table: SQLTableSchema) -> tuple[tuple[Hashable, ...], ...]:
    return tuple(
        sorted(
            (
                tuple(foreign_key.columns),
                foreign_key.foreign_schema_name or "",
                foreign_key.foreign_table,
                tuple(foreign_key.foreign_columns),
            )
            for foreign_key in table.foreign_keys
        )
    )


def _structural_signature(table: SQLTableSchema) -> Hashable:
    columns = tuple(
        sorted((column.name, column.dtype, column.native_dtype, column.nullable) for column in table.columns)
    )
    return (table.is_view, columns, tuple(table.primary_key), _foreign_key_signature(table))


def _expected_count(kind: str, first: datetime.date | int, last: datetime.date | int) -> int:
    if kind == "YYYYMMDD":
        assert isinstance(first, datetime.date) and isinstance(last, datetime.date)
        return (last - first).days + 1
    if kind == "YYYYMM":
        assert isinstance(first, datetime.date) and isinstance(last, datetime.date)
        return (last.year - first.year) * 12 + last.month - first.month + 1
    assert isinstance(first, int) and isinstance(last, int)
    return last - first + 1


def _format_value(kind: str, value: datetime.date | int, width: int | None = None) -> str:
    if kind == "YYYYMMDD":
        assert isinstance(value, datetime.date)
        return value.strftime("%Y%m%d")
    if kind == "YYYYMM":
        assert isinstance(value, datetime.date)
        return value.strftime("%Y%m")
    if kind == "YEAR":
        return str(value)
    assert isinstance(value, int)
    return str(value).zfill(width or 1)


def _missing_values(variations: list[_ParsedTableName]) -> list[datetime.date | int]:
    kind = variations[0].kind
    values = sorted({variation.value for variation in variations})
    first = values[0]
    last = values[-1]
    if kind == "YYYYMMDD":
        assert isinstance(first, datetime.date) and isinstance(last, datetime.date)
        present = set(values)
        return [
            first + datetime.timedelta(days=offset)
            for offset in range((last - first).days + 1)
            if first + datetime.timedelta(days=offset) not in present
        ]
    if kind == "YYYYMM":
        assert isinstance(first, datetime.date) and isinstance(last, datetime.date)
        present = set(values)
        missing: list[datetime.date | int] = []
        current = first
        while current <= last:
            if current not in present:
                missing.append(current)
            current = (
                current.replace(year=current.year + 1, month=1)
                if current.month == 12
                else current.replace(month=current.month + 1)
            )
        return missing
    assert isinstance(first, int) and isinstance(last, int)
    present = set(values)
    return [value for value in range(first, last + 1) if value not in present]


def _summarize_members(variations: list[_ParsedTableName]) -> str:
    kind = variations[0].kind
    variations = sorted(variations, key=lambda variation: variation.value)
    unique_values = sorted({variation.value for variation in variations})
    width = None
    if kind == "NUM":
        widths = {len(variation.text) for variation in variations}
        exact_values = list(dict.fromkeys(variation.text for variation in variations))
        if len(widths) > 1 or len(exact_values) != len(unique_values):
            if len(exact_values) <= _MAX_LISTED_VALUES:
                return f"Available NUM values: {', '.join(exact_values)}"
            edge_count = _MAX_EXAMPLE_VALUES // 2
            examples = exact_values[:edge_count] + exact_values[-edge_count:]
            return f"Members: {len(exact_values)} mixed-width NUM values; examples: {', '.join(examples)}"
        width = len(variations[0].text)
    first = unique_values[0]
    last = unique_values[-1]
    expected = _expected_count(kind, first, last)
    missing_count = expected - len(unique_values)
    label = "Partitions" if kind != "NUM" else "Members"

    if missing_count == 0:
        return (
            f"{label}: {kind} from {_format_value(kind, first, width)} "
            f"to {_format_value(kind, last, width)} ({len(unique_values)} total)"
        )

    if missing_count <= _MAX_LISTED_MISSING_VALUES:
        missing = _missing_values(variations)
        formatted = ", ".join(_format_value(kind, value, width) for value in missing)
        return (
            f"{label}: {kind} from {_format_value(kind, first, width)} "
            f"to {_format_value(kind, last, width)}, except {formatted}"
        )

    if len(unique_values) <= _MAX_LISTED_VALUES:
        formatted = ", ".join(_format_value(kind, value, width) for value in unique_values)
        return f"Available {kind} values: {formatted}"

    return (
        f"{label}: {len(unique_values)} sparse {kind} values from {_format_value(kind, first, width)} "
        f"to {_format_value(kind, last, width)}; full list omitted"
    )


def group_tables_for_formatting(schema: SQLSchema) -> list[_TableRenderGroup]:
    referenced_table_keys = {
        (foreign_key.foreign_schema_name, foreign_key.foreign_table)
        for table in schema.tables
        for foreign_key in table.foreign_keys
    }
    variations: list[_ParsedTableName | None] = []
    keys: list[Hashable | None] = []
    grouped_indices: dict[Hashable, list[int]] = defaultdict(list)

    for index, table in enumerate(schema.tables):
        variation = _parse_name(table.name)
        variations.append(variation)
        table_key = (table.schema_name, table.name)
        # Keep concrete FK targets visible because grouped rendering does not rewrite relationships.
        if variation is None or table_key in referenced_table_keys:
            keys.append(None)
            continue
        candidate_key = (table.schema_name, variation.pattern, _structural_signature(table))
        keys.append(candidate_key)
        grouped_indices[candidate_key].append(index)

    result: list[_TableRenderGroup] = []
    emitted: set[Hashable] = set()
    for index, table in enumerate(schema.tables):
        current_key = keys[index]
        if current_key is None or len(grouped_indices[current_key]) < 2:
            result.append(_TableRenderGroup.from_table(table))
            continue
        if current_key in emitted:
            continue
        emitted.add(current_key)
        indices = grouped_indices[current_key]
        group_variations = [variations[i] for i in indices]
        assert all(variation is not None for variation in group_variations)
        parsed_variations = [variation for variation in group_variations if variation is not None]
        result.append(
            _TableRenderGroup(
                members=tuple(schema.tables[i] for i in indices),
                display_name=parsed_variations[0].pattern,
                member_summary=_summarize_members(parsed_variations),
            )
        )
    return result
