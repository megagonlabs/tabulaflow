import asyncio
import json
from dataclasses import dataclass
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

Concepts:
- A **section** is a collection of semantically relevant columns that describe one aspect of the table.
  - The name of the section should be a short noun phrase.
  - One column must be in exactly one section.

Instructions:
- You will be given the current list of sections, and a list of new columns that need to be added.
- You are allowed to add new sections, merge existing sections, or edit the name or description of an existing section.
- You must ensure the section exists before assigning a column to it.
""".strip()

COLUMN_GROUP_PROMPT = """
You are a helpful database expert that identify groups among the columns in a SQL table.

Concepts:
- A **group** consists of columns that are highly similar based on the following criteria:
  - They share a common prefix or suffix.
  - They have the same data type.
  - They contain the same set of values.
- If there are no similar columns that satisfy the above criteria, create a new group with a single column.
- The name of the group should be:
  - If there is only one column, the name of the column.
  - If there are multiple columns, a pseudo-regex pattern that captures the column name pattern.
    - You can use the regex syntax (e.g. "person_[0-9]+", "age_(male|female)")
    - You can use the `{...}` template syntax (e.g. "revenue_{YYYYMM}") with description to explain the template.
    - Prioritize readability. Don't use complex regexes.
- The description should be:
  - null if there is only one column or the pseudo-regex already fully captures the column name pattern.
  - a short description of the pattern variations otherwise.
- One column must be in exactly one group.

Instructions:
- You will be given the current list of groups, and a list of new columns that need to be added.
- You are allowed to add new groups, merge existing groups, or edit the name or description of an existing group.
- You must ensure the group exists before assigning a column to it. The name must match exactly the name of the group.
""".strip()


@dataclass
class HTableSchemaSynthesizer:
    llm: str = "gpt-4o"
    batch_size: int = 20
    temperature: float = 0.0

    async def build_sections(self, table: SQLTableSchema) -> list[HTableSection]:
        clusterer = LLMClusterer(
            llm=self.llm,
            instruction=SECTION_PROMPT,
            format_fn=lambda name, column: json.dumps({"column_name": name, "datatype": column.dtype}),
            batch_size=self.batch_size,
            temperature=self.temperature,
        )
        clusters = await clusterer.cluster_async([c.name for c in table.columns], table.columns)

        all_groups = await asyncio.gather(
            *[self.build_groups([table.columns[idx] for idx in c.item_indexes]) for c in clusters]
        )

        return [
            HTableSection(
                name=c.name,
                description=c.description,
                column_groups=groups,
            )
            for c, groups in zip(clusters, all_groups)
        ]

    async def build_groups(self, columns: list[SQLColumnSchema]) -> list[HColumnGroup]:
        clusterer = LLMClusterer(
            llm=self.llm,
            instruction=COLUMN_GROUP_PROMPT,
            format_fn=lambda name, column: json.dumps({"column_name": name, "datatype": column.dtype}),
            batch_size=self.batch_size,
            temperature=self.temperature,
        )
        clusters = await clusterer.cluster_async([c.name for c in columns], columns)

        return [
            HColumnGroup(name=c.name, description=c.description, columns=[columns[idx] for idx in c.item_indexes])
            for c in clusters
        ]

    async def run(self, table: SQLTableSchema) -> HTableSchema:
        sections = await self.build_sections(table)

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
    batch_size: int = 20
    temperature: float = 0.0

    async def run(self, db_connector: BaseAsyncSQLDBConnector) -> HSQLSchema:
        schema = db_connector.schema

        table_synthesizer = HTableSchemaSynthesizer(
            llm=self.llm,
            batch_size=self.batch_size,
            temperature=self.temperature,
        )

        table_hschemas = await asyncio.gather(*[table_synthesizer.run(table) for table in schema.tables])

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
