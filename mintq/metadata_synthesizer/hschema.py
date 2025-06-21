import asyncio
import json
import os
import collections
from dataclasses import dataclass, field
from typing import Any
from mintq.schema import (
    SQLTableSchema,
    SQLColumnSchema,
    HTableSection,
    HColumnGroup,
    HSQLSchema,
    HTableGroup,
    ForeignKeySchema,
)
from mintq.metadata_synthesizer.clusterer import LLMClusterer, AffixClusterer, BaseClusterer
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.formatters import SQLDefaultSchemaFormatter
from mintq.config import config

SECTION_PROMPT = """
You are a helpful database expert that organizes the columns in a SQL table into sections.
- A **section** is a collection of semantically relevant columns that describe one aspect of the table.
  - The name of the section should be a short noun phrase.
  - The description of the section should be a concise short phrase that summarizes the columns available in the section.
  - One column must belong to exactly one section.
- Key columns such as "id", "name", and primary entity attributes should be placed in the "Core" section.
  - For event-based entities (e.g., disasters, tournaments), consider including id, name, date, location, outcome, and principal participants as core attributes.
  - For non-event entities (e.g., products, customers), consider including id, name, and domain-relevant attributes (e.g., height, weight for athletes) as core attributes.
  - Foreign key columns should always be included in the "Core" section.
""".strip()


@dataclass
class TableSectionSynthesizer:
    llm: str = "gpt-4o"
    batch_size: int = 10
    temperature: float = 0.0
    section_clusterer_: BaseClusterer | None = None

    def _column_digest(self, column: SQLColumnSchema) -> Any:
        """
        The digest of a column includes its data type, values set if categorical, primary key type, and foreign keys.
        Columns in the same group must have the same digest.
        """
        is_categorical = (
            column.dtype in ("TEXT", "VARCHAR")
            and column.num_unique
            and column.unique_ratio
            and 0 < column.num_unique <= 20
            and column.unique_ratio < 0.01
        )
        values = tuple(sorted(column.examples)) if is_categorical else None
        foreign_keys = tuple(
            sorted(
                [
                    (
                        tuple([c if c != column.name else "[MASK]" for c in fk.columns]),
                        fk.foreign_schema_name,
                        fk.foreign_table,
                        tuple(fk.foreign_columns),
                    )
                    for fk in column.foreign_keys
                ]
            )
        )
        return (column.dtype, is_categorical, values, column.primary_key_type, foreign_keys)

    @staticmethod
    def _format_column_group(cg: HColumnGroup) -> str:
        return SQLDefaultSchemaFormatter().format_column(
            SQLColumnSchema(
                name=cg.name,
                dtype=cg.dtype,
                nullable=cg.nullable,
                null_ratio=cg.null_ratio,
                num_unique=cg.num_unique,
                unique_ratio=cg.unique_ratio,
                examples=cg.examples,
                primary_key_type=cg.primary_key_type,
                foreign_keys=cg.foreign_keys,
            )
        )

    async def run_async(self, tables: list[SQLTableSchema]) -> list[HTableSection]:
        digest2columns = collections.defaultdict(list)
        for column in tables[0].columns:
            digest2columns[self._column_digest(column)].append(column)

        name2column = {c.name: c for c in tables[0].columns}
        column_groups = []
        clusterer = AffixClusterer()
        for _, columns_with_same_digest in digest2columns.items():
            clusters = await clusterer.cluster_async(
                [c.name for c in columns_with_same_digest], columns_with_same_digest
            )
            for cluster in clusters:
                cols = [name2column[name] for name in cluster.item_names]
                column_groups.append(
                    HColumnGroup(
                        name=cluster.name,
                        description=cluster.description,
                        column_names=cluster.item_names,
                        dtype=cols[0].dtype,
                        nullable=any(c.nullable for c in cols),
                        null_ratio=sum(c.null_ratio for c in cols) / len(cols),
                        num_unique=cols[0].num_unique,
                        unique_ratio=cols[0].unique_ratio,
                        examples=cols[0].examples,
                        primary_key_type=cols[0].primary_key_type,
                        foreign_keys=[
                            ForeignKeySchema(
                                # replace the column name with the column group name
                                columns=[s if s != cols[0].name else cluster.name for s in fk.columns],
                                foreign_schema_name=fk.foreign_schema_name,
                                foreign_table=fk.foreign_table,
                                foreign_columns=fk.foreign_columns,
                            )
                            for fk in cols[0].foreign_keys
                        ],
                    )
                )

        self.section_clusterer_ = LLMClusterer(
            llm=self.llm,
            instruction=SECTION_PROMPT,
            format_fn=lambda name, column_group: json.dumps(
                {"column_name": name, "column_description": self._format_column_group(column_group)}
            ),
            batch_size=self.batch_size,
            temperature=self.temperature,
        )
        clusters = await self.section_clusterer_.cluster_async([cg.name for cg in column_groups], column_groups)
        name2cg = {cg.name: cg for cg in column_groups}
        return [
            HTableSection(
                name=cluster.name,
                description=cluster.description,
                column_groups=[name2cg[name] for name in cluster.item_names],
            )
            for cluster in clusters
        ]


@dataclass
class HSchemaSynthesizer:
    llm: str = "gpt-4o"
    batch_size: int = 10
    temperature: float = 0.0
    table_section_synthesizers_: list[TableSectionSynthesizer] = field(default_factory=list)

    def _table_digest(self, table: SQLTableSchema) -> Any:
        """
        The digest of a table includes its column names and data types, the primary key, and the foreign keys.
        Tables in the same group must have the same digest.
        """
        schema_name = table.schema_name
        columns = tuple(sorted([(c.name, c.dtype) for c in table.columns]))
        primary_key = tuple(sorted(table.primary_key))
        foreign_keys = tuple(
            sorted(
                [
                    (tuple(fk.columns), fk.foreign_schema_name, fk.foreign_table, tuple(fk.foreign_columns))
                    for fk in table.foreign_keys
                ]
            )
        )
        return (schema_name, columns, primary_key, foreign_keys)

    async def _run_async(self, db_connector: BaseAsyncSQLDBConnector) -> HSQLSchema:
        schema = db_connector.schema

        digest2tables = collections.defaultdict(list)
        for table in schema.tables:
            digest2tables[self._table_digest(table)].append(table)

        table_groups = []
        clusterer = AffixClusterer()
        name2table = {t.name: t for t in schema.tables}
        for _, tables in digest2tables.items():
            clusters = await clusterer.cluster_async([t.name for t in tables], tables)
            for c in clusters:
                table_groups.append((c.name, [name2table[name] for name in c.item_names]))

        self.table_section_synthesizers_ = [
            TableSectionSynthesizer(
                llm=self.llm,
                batch_size=self.batch_size,
                temperature=self.temperature,
            )
            for _ in table_groups
        ]

        all_sections = await asyncio.gather(
            *[synth.run_async(tables) for synth, (_, tables) in zip(self.table_section_synthesizers_, table_groups)]
        )

        return HSQLSchema(
            name=schema.name,
            table_groups=[
                HTableGroup(
                    name=name,
                    table_names=[t.name for t in tables],
                    schema_name=tables[0].schema_name,
                    primary_key=tables[0].primary_key,
                    foreign_keys=tables[0].foreign_keys,
                    sections=sections,
                )
                for ((name, tables), sections) in zip(table_groups, all_sections)
            ],
        )

    async def run_async(self, db_connector: BaseAsyncSQLDBConnector) -> HSQLSchema:
        hschema_cache_dir = os.path.join(config.cache_dir, "hschema")
        os.makedirs(hschema_cache_dir, exist_ok=True)

        cache_path = os.path.join(hschema_cache_dir, f"{db_connector.global_id}.json")
        if config.cache_enabled and os.path.exists(cache_path):
            if config.cache_refresh:
                os.remove(cache_path)
            else:
                with open(cache_path, "r") as f:
                    return HSQLSchema.model_validate_json(f.read())

        hschema = await self._run_async(db_connector)
        if config.cache_enabled:
            with open(cache_path, "w") as f:
                f.write(hschema.model_dump_json())
        return hschema
