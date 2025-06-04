import asyncio
import json
from dataclasses import dataclass, field
from mintq.schema import (
    SQLTableSchema,
    SQLColumnSchema,
    HTableSection,
    HColumnGroup,
    HSQLSchema,
    HTableGroup,
    HTableSchema,
)
from mintq.metadata_synthesizer.llm_clusterer import LLMClusterer
from mintq.db_connector import BaseAsyncSQLDBConnector


SECTION_PROMPT = """
You are a helpful database expert that organizes the columns in a SQL table into sections.
- A **section** is a collection of semantically relevant columns that describe one aspect of the table.
  - The name of the section should be a short noun phrase.
  - The description of the section should be a concise short phrase that summarizes the columns available in the section.
  - One column must belong to exactly one section.
- Key columns such as "id", "name", and primary entity attributes should be placed in the "Core" section.
  - For event-based entities (e.g., disasters, tournaments), include id, name, date, location, and principal participants as core attributes.
  - For non-event entities (e.g., products, customers), include id, name, and domain-relevant attributes (e.g., height, weight for athletes) as core attributes.
  - For join tables, include foreign key columns as core attributes.
""".strip()

COLUMN_GROUP_PROMPT = """
You are a helpful database expert that identify groups among the columns in a SQL table.
- A **group** is defined as a set of columns that meet all the following criteria:
  - Share a common prefix or suffix, varying only by digits (e.g., "revenue_202401", "revenue_202402") or a short standardized code (e.g., airport codes).
    - Do NOT group columns that differ by a word with distinct semantic meaning (e.g., "age_student" and "age_teacher" must not be grouped together).
  - Have identical data types.
  - Contain the same set of values.
- If a column does not meet the above criteria with any other column, place it in a singleton group.
- Each column must belong to exactly one group.
- For singleton groups:
  - Use the column name as the group name.
  - Set the description to null.
- For non-singleton groups:
  - Use the shared prefix or suffix with a placeholder for the varying component (e.g., "revenue_{YYYYMM}") as the group name.
  - Provide a brief description indicating the range or type of variations (e.g., "YYYYMM from 201608 to 202405").
""".strip()


@dataclass
class HTableSchemaSynthesizer:
    llm: str = "gpt-4o"
    batch_size: int = 10
    temperature: float = 0.0
    section_clusterer_: LLMClusterer | None = None
    column_group_clusterers_: dict[str, LLMClusterer] = field(default_factory=dict)

    async def build_sections_async(self, table: SQLTableSchema) -> list[HTableSection]:
        self.section_clusterer_ = LLMClusterer(
            llm=self.llm,
            instruction=SECTION_PROMPT,
            format_fn=lambda name, column: json.dumps({"column_name": name, "datatype": column.dtype}),
            batch_size=self.batch_size,
            temperature=self.temperature,
        )
        clusters = await self.section_clusterer_.cluster_async([c.name for c in table.columns], table.columns)

        name2column = {c.name: c for c in table.columns}
        all_groups = await asyncio.gather(
            *[self.build_groups_async(c.name, [name2column[name] for name in c.item_names]) for c in clusters]
        )

        return [
            HTableSection(
                name=c.name,
                description=c.description,
                column_groups=groups,
            )
            for c, groups in zip(clusters, all_groups)
        ]

    async def build_groups_async(self, section_name: str, columns: list[SQLColumnSchema]) -> list[HColumnGroup]:
        clusterer = LLMClusterer(
            llm=self.llm,
            instruction=COLUMN_GROUP_PROMPT,
            format_fn=lambda name, column: json.dumps({"column_name": name, "datatype": column.dtype}),
            batch_size=self.batch_size,
            temperature=self.temperature,
        )
        self.column_group_clusterers_[section_name] = clusterer
        clusters = await clusterer.cluster_async([c.name for c in columns], columns)

        name2column = {c.name: c for c in columns}
        return [
            HColumnGroup(name=c.name, description=c.description, columns=[name2column[name] for name in c.item_names])
            for c in clusters
        ]

    async def run_async(self, table: SQLTableSchema) -> HTableSchema:
        sections = await self.build_sections_async(table)

        return HTableSchema(
            name=table.name,
            schema_name=table.schema_name,
            primary_key=table.primary_key,
            num_rows=table.num_rows,
            sections=sections,
        )


@dataclass
class HSchemaSynthesizer:
    llm: str = "gpt-4o"
    batch_size: int = 10
    temperature: float = 0.0
    table_synthesizers_: dict[str, HTableSchemaSynthesizer] = field(default_factory=dict)

    async def run_async(self, db_connector: BaseAsyncSQLDBConnector) -> HSQLSchema:
        schema = db_connector.schema

        self.table_synthesizers_ = {
            table.name: HTableSchemaSynthesizer(
                llm=self.llm,
                batch_size=self.batch_size,
                temperature=self.temperature,
            )
            for table in schema.tables
        }

        table_hschemas = await asyncio.gather(
            *[self.table_synthesizers_[table.name].run_async(table) for table in schema.tables]
        )

        return HSQLSchema(
            name=schema.name,
            table_groups=[
                HTableGroup(
                    name=table.name,
                    tables=[table],
                )
                for table in table_hschemas
            ],
            foreign_keys=schema.foreign_keys,
        )
