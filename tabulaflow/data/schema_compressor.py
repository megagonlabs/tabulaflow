import copy
import collections
from typing import Any, Hashable, Protocol, TypeVar
from dataclasses import dataclass, field
import datetime
import re
from tabulaflow.core import TableNamePattern, SQLSchema, SQLTableSchema, SQLColumnSchema, ForeignKeySchema


T = TypeVar("T")


class BaseClusterFunc(Protocol[T]):
    def extract(self, name: str) -> tuple[str, T | None]: ...

    def summarize(self, variations: list[T]) -> str | None: ...


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
        if year < 1000:
            return name, None
        try:
            parsed_date = datetime.date(year, month, day)
        except ValueError:
            return name, None
        pattern = re.sub(r"\d{4}\d{2}\d{2}", "{YYYYMMDD}", name, count=1)
        return pattern, parsed_date

    def summarize(self, variations: list[datetime.date]) -> str | None:
        dates = sorted(set(variations))
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
            return "YYYYMMDD IN {" + ",".join(d.strftime("%Y%m%d") for d in dates) + "}"
        res = f"YYYYMMDD from {a.strftime('%Y%m%d')} to {b.strftime('%Y%m%d')}"
        if missing_dates:
            res += f" except {', '.join([d.strftime('%Y%m%d') for d in missing_dates])}"
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
        if year < 1000 or not (1 <= month <= 12):
            return name, None
        pattern = re.sub(r"\d{4}\d{2}", "{YYYYMM}", name, count=1)
        return pattern, datetime.date(year, month, day)

    def summarize(self, variations: list[datetime.date]) -> str | None:
        dates = sorted(set(variations))
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
            return "YYYYMM IN {" + ",".join(d.strftime("%Y%m") for d in dates) + "}"
        res = f"YYYYMM from {a.strftime('%Y%m')} to {b.strftime('%Y%m')}"
        if missing_dates:
            res += f" except {', '.join([d.strftime('%Y%m') for d in missing_dates])}"
        return res


@dataclass
class YearAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, int | None]:
        match = re.search(r"(?<!\d)\d{4}(?!\d)", name)
        if not match:
            return name, None
        year = int(match.group())
        if year < 1000:
            return name, None
        pattern = re.sub(r"\d{4}", "{YEAR}", name, count=1)
        return pattern, year

    def summarize(self, variations: list[int]) -> str | None:
        years = sorted(set(variations))
        a = years[0]
        b = years[-1]
        years_set = set(years)
        missing_years = [y for y in range(a, b + 1) if y not in years_set]
        if len(missing_years) / (b - a + 1) > self.max_missing_ratio:
            return "YEAR IN {" + ",".join(str(y) for y in years) + "}"
        res = f"YEAR from {a} to {b}"
        if missing_years:
            res += f" except {', '.join([str(y) for y in missing_years])}"
        return res


@dataclass
class IndexAffixClusterFunc:
    max_missing_ratio: float = 0.2

    def extract(self, name: str) -> tuple[str, str | None]:
        match = re.search(r"\d+", name)
        if not match:
            return name, None
        pattern = re.sub(r"\d+", "{NUM}", name, count=1)
        return pattern, str(match.group())

    def summarize(self, variations: list[str]) -> str | None:
        unique = sorted(set(variations), key=lambda s: int(s))
        int_to_str = {int(s): s for s in unique}
        ints = list(int_to_str.keys())
        a = ints[0]
        b = ints[-1]
        int_set = set(ints)
        missing = [i for i in range(a, b + 1) if i not in int_set]
        if len(missing) / (b - a + 1) > self.max_missing_ratio:
            return "NUM IN {" + ",".join(unique) + "}"
        res = f"NUM from {int_to_str[a]} to {int_to_str[b]}"
        if missing:
            res += f" except {', '.join(str(i) for i in missing)}"
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
            tuple(sorted(zip(fk.columns, fk.foreign_columns, strict=True))),
            fk.foreign_schema_name,
            fk.foreign_table,
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
        assert all(c.name == columns[0].name for c in columns)
        assert all(c.dtype == columns[0].dtype for c in columns)
        all_null_ratio = [c.null_ratio for c in columns if c.null_ratio is not None]
        merged_null_ratio = sum(all_null_ratio) / len(all_null_ratio) if all_null_ratio else None
        merged_num_unique = max([c.num_unique for c in columns if c.num_unique is not None], default=None)
        merged_unique_ratio = max([c.unique_ratio for c in columns if c.unique_ratio is not None], default=None)
        merged_examples = list(dict.fromkeys(sum([c.examples for c in columns], [])))[:20]

        # Use the first non-None json_schema among the columns being merged
        merged_json_schema = next((c.json_schema for c in columns if c.json_schema is not None), None)
        merged_native_dtype = next((c.native_dtype for c in columns if c.native_dtype is not None), None)

        return SQLColumnSchema(
            name=columns[0].name,
            dtype=columns[0].dtype,
            native_dtype=merged_native_dtype,
            description=columns[0].description,
            nullable=any(c.nullable for c in columns),
            null_ratio=merged_null_ratio,
            num_unique=merged_num_unique,
            unique_ratio=merged_unique_ratio,
            examples=merged_examples,
            json_schema=merged_json_schema,
        )

    def _get_patterns(self, names: list[str]) -> list[TableNamePattern]:
        """Example:
        _get_patterns(names=["revenue_20200101", "revenue_20200102", "revenue_20200103", "profit_20200101", "profit_20200102", "profit_20200103"])
        returns: [
          TableNamePattern(pattern="revenue_YYYYMMDD", comment="YYYYMMDD from 20200101 to 20200103", original_names=["revenue_20200101", "revenue_20200102", "revenue_20200103"]),
          TableNamePattern(pattern="profit_YYYYMMDD", comment="YYYYMMDD from 20200101 to 20200103", original_names=["profit_20200101", "profit_20200102", "profit_20200103"]),
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
                name_description = func.summarize(variations)
                if name_description is not None:
                    remaining = [name for name in remaining if name not in group_names]
                    res.append(TableNamePattern(pattern=pattern, comment=name_description, original_names=group_names))

        for name in remaining:
            res.append(TableNamePattern(pattern=name, original_names=[name]))

        return res

    def _merge_tables(self, tables: list[SQLTableSchema]) -> SQLTableSchema:
        if len(tables) == 1:
            return tables[0]

        # Prefer a table with num_rows set, ensuring it's not a shallow-copied table (see sql_conn.py)
        base_table = next((t for t in tables if t.num_rows is not None), tables[0])
        merged_table = copy.deepcopy(base_table)
        merged_table.name_patterns = self._get_patterns([t.name for t in tables])
        # Match columns by name (not index) since tables with the same digest
        # may have different column orders.
        col_name_to_columns: dict[str, list[SQLColumnSchema]] = collections.defaultdict(list)
        for t in tables:
            for c in t.columns:
                col_name_to_columns[c.name].append(c)
        merged_table.columns = [self._merge_columns(col_name_to_columns[c.name]) for c in merged_table.columns]
        return merged_table

    def compress(self, schema: SQLSchema) -> SQLSchema:
        schema = copy.deepcopy(schema)

        digest2tables = collections.defaultdict(list)
        for table in schema.tables:
            digest2tables[self._table_digest(table, schema)].append(table)

        schema.tables = [self._merge_tables(tables) for tables in digest2tables.values()]
        return schema
