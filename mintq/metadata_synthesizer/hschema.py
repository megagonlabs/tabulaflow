import asyncio
from dataclasses import dataclass
from mintq.schema import (
    SQLTableSchema,
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
- A section is a collection of semantically similar columns that describe one aspect of the table.
  - The name of the section should be a short noun phrase.
  - One column must be in exactly one section.

Requirements:
- You will be given the current list of sections, and a list of new columns that need to be added.
- You are allowed to add new sections, or update the existing sections.
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
            format_fn=lambda name, column: f"- {name}: {column.dtype}",
            batch_size=self.batch_size,
            temperature=self.temperature,
        )
        sections = await clusterer.cluster_async([c.name for c in table.columns], table.columns)

        return [
            HTableSection(
                name=s.name,
                description=s.description,
                column_groups=[
                    HColumnGroup(name=table.columns[idx].name, columns=[table.columns[idx]]) for idx in s.item_indexes
                ],
            )
            for s in sections
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
