import copy
import collections
from typing import Any, Hashable, Protocol, Sequence, TypeVar
from dataclasses import dataclass, field
import datetime
import re
from mintq.schema import (
    SQLSchema,
    SQLTableSchema,
    SQLColumnSchema,
    ForeignKeySchema,
)


T = TypeVar("T")


class BaseClusterFunc(Protocol[T]):
    def extract(self, name: str) -> tuple[str, T | None]: ...

    def summarize(self, variations: list[T]) -> str | None: ...


@dataclass
class IndexAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, int | None]:
        match = re.search(r"\d+", name)
        if not match:
            return name, None
        pattern = re.sub(r"\d+", "{#}", name, count=1)
        return pattern, int(match.group())

    def summarize(self, variations: list[int]) -> str | None:
        indexes = sorted(variations)
        a = indexes[0]
        b = indexes[-1]
        missing_indexes = [i for i in range(a, b + 1) if i not in indexes]
        if len(missing_indexes) / (b - a + 1) > self.max_missing_ratio:
            return None
        res = f"# from {a} to {b}"
        if missing_indexes:
            res += f" except {', '.join([str(i) for i in missing_indexes])}"
        return res


@dataclass
class YearAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, int | None]:
        match = re.search(r"(?<!\d)\d{4}(?!\d)", name)
        if not match:
            return name, None
        year = int(match.group())
        if year < 1000 or year > datetime.datetime.now().year:
            return name, None
        pattern = re.sub(r"\d{4}", "{YEAR}", name, count=1)
        return pattern, year

    def summarize(self, variations: list[int]) -> str | None:
        years = sorted(variations)
        a = years[0]
        b = years[-1]
        years_set = set(years)
        missing_years = [y for y in range(a, b + 1) if y not in years_set]
        if len(missing_years) / (b - a + 1) > self.max_missing_ratio:
            return None
        res = f"YEAR from {a} to {b}"
        if missing_years:
            res += f" except {', '.join([str(y) for y in missing_years])}"
        return res


@dataclass
class YearMonthAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, datetime.date | None]:
        match = re.search(r"(?<!\d)\d{4}\d{2}(?!\d)", name)
        if not match:
            return name, None
        year = int(match.group()[:4])
        month = int(match.group()[4:])
        day = 1
        if (
            year < 1000
            or month < 12
            and datetime.date(year, month + 1, day) > datetime.date.today()
            or month == 12
            and datetime.date(year + 1, 1, day) > datetime.date.today()
        ):
            return name, None
        pattern = re.sub(r"\d{4}\d{2}", "{YYYYMM}", name, count=1)
        return pattern, datetime.date(year, month, day)

    def summarize(self, variations: list[datetime.date]) -> str | None:
        dates = sorted(variations)
        a = dates[0]
        b = dates[-1]
        dates_set = set(dates)
        missing_dates = []
        current = a
        while current <= b:
            if current not in dates_set:
                missing_dates.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        if len(missing_dates) / ((b - a).days + 1) > self.max_missing_ratio:
            return None
        res = f"YYYYMM from {a.strftime('%Y%m')} to {b.strftime('%Y%m')}"
        if missing_dates:
            res += f" except {', '.join([d.strftime('%Y%m') for d in missing_dates])}"
        return res


@dataclass
class DateAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, datetime.date | None]:
        match = re.search(r"(?<!\d)\d{4}\d{2}\d{2}(?!\d)", name)
        if not match:
            return name, None
        year = int(match.group()[:4])
        month = int(match.group()[4:6])
        day = int(match.group()[6:])
        if year < 1000 or datetime.date(year, month, day) > datetime.date.today():
            return name, None
        pattern = re.sub(r"\d{4}\d{2}\d{2}", "{YYYYMMDD}", name, count=1)
        return pattern, datetime.date(year, month, day)

    def summarize(self, variations: list[datetime.date]) -> str | None:
        dates = sorted(variations)
        a = dates[0]
        b = dates[-1]
        dates_set = set(dates)
        missing_dates = []
        current = a
        while current <= b:
            if current not in dates_set:
                missing_dates.append(current)
            current += datetime.timedelta(days=1)
        if len(missing_dates) / ((b - a).days + 1) > self.max_missing_ratio:
            return None
        res = f"YYYYMMDD from {a.strftime('%Y%m%d')} to {b.strftime('%Y%m%d')}"
        if missing_dates:
            res += f" except {', '.join([d.strftime('%Y%m%d') for d in missing_dates])}"
        return res


@dataclass
class SchemaCompressor:
    """
    Compresses the schema by iteratively merging tables with the same digest.
    """

    name_cluster_funcs: list[BaseClusterFunc[Any]] = field(
        default_factory=lambda: [
            DateAffixClusterFunc(),
            YearMonthAffixClusterFunc(),
            YearAffixClusterFunc(),
            IndexAffixClusterFunc(),
        ]
    )

    def _foreign_key_digest(self, fk: ForeignKeySchema, table: SQLTableSchema) -> tuple[Any, ...]:
        return (
            table.schema_name,
            table.name,
            tuple(sorted(fk.columns)),
            fk.foreign_schema_name,
            fk.foreign_table,
            tuple(sorted(fk.foreign_columns)),
        )

    def _table_digest(self, table: SQLTableSchema, full_schema: SQLSchema) -> Hashable:
        """
        The digest of a table includes:
        - the schema name
        - column names and data types
        - the primary key
        - the outgoing foreign keys
        - the incoming foreign keys
        """
        schema_name = table.schema_name
        columns = tuple(sorted([(c.name, c.dtype) for c in table.columns]))
        primary_key = tuple(sorted(table.primary_key))
        out_foreign_keys = tuple(sorted([self._foreign_key_digest(fk, table) for fk in table.foreign_keys]))
        in_foreign_keys = tuple(
            sorted(
                [
                    self._foreign_key_digest(fk, t)
                    for t in full_schema.tables
                    for fk in t.foreign_keys
                    if (fk.foreign_schema_name, fk.foreign_table) == (table.schema_name, table.name)
                ]
            )
        )
        return (schema_name, columns, primary_key, out_foreign_keys, in_foreign_keys)

    def _merge_columns(self, columns: list[SQLColumnSchema]) -> SQLColumnSchema:
        return SQLColumnSchema(
            name=columns[0].name,
            dtype=columns[0].dtype,
            description=columns[0].description,
            nullable=any(c.nullable for c in columns),
            null_ratio=sum(c.null_ratio for c in columns) / len(columns),
            num_unique=max([c.num_unique for c in columns if c.num_unique is not None], default=None),
            unique_ratio=max([c.unique_ratio for c in columns if c.unique_ratio is not None], default=None),
            examples=list(dict.fromkeys(sum([c.examples for c in columns], []))),
            primary_key_type=columns[0].primary_key_type,
            foreign_keys=columns[0].foreign_keys,
        )

    def _describe_name(self, names: list[str]) -> Sequence[tuple[str, str | None, list[str]]]:
        """Example:
        _describe_name(names=["revenue_20200101", "revenue_20200102", "revenue_20200103", "profit_20200101", "profit_20200102", "profit_20200103"])
        returns: [
          ("revenue_YYYYMMDD", "YYYYMMDD from 20200101 to 20200103", ["revenue_20200101", "revenue_20200102", "revenue_20200103"]),
          ("profit_YYYYMMDD", "YYYYMMDD from 20200101 to 20200103", ["profit_20200101", "profit_20200102", "profit_20200103"]),
        ]
        """
        res = []
        remaining = names
        for func in self.name_cluster_funcs:
            groups = collections.defaultdict(list)
            for name in remaining:
                pattern, variation = func.extract(name)
                groups[pattern].append((name, variation))

            for pattern, group in groups.items():
                group_names = [name for name, _ in group]
                variations = [v for _, v in group]
                if len(group) == 1 or any(v is None for v in variations):
                    continue
                remaining = [name for name in remaining if name not in group_names]
                name_description = func.summarize(variations)
                if name_description is not None:
                    res.append((pattern, name_description, group_names))

        if remaining:
            res.append(("{" + ",".join(remaining) + "}", None, remaining))  # type: ignore
        return res

    async def run_async(self, schema: SQLSchema) -> SQLSchema:
        schema = copy.deepcopy(schema)

        # We don't allow merging already merged tables
        is_merged = set()

        while True:
            digest2tables = collections.defaultdict(list)
            for table in schema.tables:
                if table.name not in is_merged:
                    digest2tables[self._table_digest(table, schema)].append(table)

            if not digest2tables:  # All tables have been merged once
                return schema

            largest_group = max(digest2tables.values(), key=len)
            if len(largest_group) == 1:  # No two tables have the same digest
                return schema

            for group_name, group_name_description, original_names in self._describe_name(
                [t.name for t in largest_group]
            ):
                tables_to_merge = [t for t in largest_group if t.name in original_names]
                merged_table = copy.deepcopy(largest_group[0])
                merged_table.name = group_name
                merged_table.name_description = group_name_description
                merged_table.original_names = original_names
                for i in range(len(merged_table.columns)):
                    merged_table.columns[i] = self._merge_columns([t.columns[i] for t in tables_to_merge])

                name_mapping = {(t.schema_name, t.name): merged_table.name for t in tables_to_merge}
                new_tables = [merged_table] + [t for t in schema.tables if (t.schema_name, t.name) not in name_mapping]
                for table in new_tables:
                    for fk in table.foreign_keys:
                        if (fk.foreign_schema_name, fk.foreign_table) in name_mapping:
                            fk.foreign_table = name_mapping[(fk.foreign_schema_name, fk.foreign_table)]

                is_merged.add(merged_table.name)

                schema.tables = new_tables
