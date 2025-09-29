import copy
import collections
from typing import Hashable, Protocol
from dataclasses import dataclass, field
import datetime
import re
from mintq.schema import (
    SQLSchema,
    SQLTableSchema,
    SQLColumnSchema,
    ForeignKeySchema,
)


class BaseClusterFunc(Protocol):
    def extract(self, name: str) -> tuple[str, str | None]: ...

    def summarize(self, variations: list[str]) -> str | None: ...


@dataclass
class IndexAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, int | None]:
        match = re.search(r"\d+", name)
        if not match:
            return name, None
        pattern = re.sub(r"\d+", "{#}", name, count=1)
        return pattern, int(match.group())

    def summarize(self, indexes: list[int]) -> str | None:
        indexes = sorted(indexes)
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

    def summarize(self, years: list[int]) -> str | None:
        years = sorted(years)
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

    def summarize(self, dates: list[datetime.date]) -> str | None:
        dates = sorted(dates)
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

    def summarize(self, dates: list[datetime.date]) -> str | None:
        dates = sorted(dates)
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

    name_cluster_funcs: list[BaseClusterFunc] = field(
        default_factory=lambda: [
            YearAffixClusterFunc(),
            YearMonthAffixClusterFunc(),
            DateAffixClusterFunc(),
            IndexAffixClusterFunc(),
        ]
    )

    def _foreign_key_digest(self, fk: ForeignKeySchema, table: SQLTableSchema) -> Hashable:
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

    def _describe_name(self, names: list[str]) -> tuple[str, str | None]:
        """Example:
        names = ["revenue_20200101", "revenue_20200102", "revenue_20200103"]
        return ("revenue_YYYYMMDD", "YYYYMMDD from 20200101 to 20200103")
        """
        candidates = [("{" + ",".join(names) + "}", None)]
        for func in self.name_cluster_funcs:
            groups = collections.defaultdict(list)
            for name in names:
                pattern, variation = func.extract(name)
                groups[pattern].append((name, variation))

            if len(groups) > 1:
                continue
            pattern = list(groups.keys())[0]
            name_description = func.summarize([v for _, v in groups[pattern]])
            if name_description is not None:
                candidates.append((pattern, name_description))

        # Choose the candidate with the shortest name + name_description
        return min(candidates, key=lambda x: len(x[0] + (x[1] or "")))

    async def run_async(self, schema: SQLSchema) -> SQLSchema:
        schema = copy.deepcopy(schema)

        while True:
            digest2tables = collections.defaultdict(list)
            for table in schema.tables:
                digest2tables[self._table_digest(table, schema)].append(table)

            largest_group = max(digest2tables.values(), key=len)
            if len(largest_group) == 1:
                return schema

            group_name, group_name_description = self._describe_name([t.name for t in largest_group])

            new_table = largest_group[0]
            new_table.name = group_name
            new_table.name_description = group_name_description
            new_table.original_names = [t.name for t in largest_group]
            for i in range(len(new_table.columns)):
                new_table.columns[i] = self._merge_columns([t.columns[i] for t in largest_group])

            name_mapping = {(t.schema_name, t.name): new_table.name for t in largest_group}
            new_tables = [new_table] + [t for t in schema.tables if (t.schema_name, t.name) not in name_mapping]
            for table in new_tables:
                for fk in table.foreign_keys:
                    if (fk.foreign_schema_name, fk.foreign_table) in name_mapping:
                        fk.foreign_table = name_mapping[(fk.foreign_schema_name, fk.foreign_table)]

            schema.tables = new_tables
