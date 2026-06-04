import argparse
from dataclasses import dataclass
from typing import ClassVar
import asyncio
import os
import json
from tabulaflow.toolhub import RunQueryTool
from tabulaflow.research.tools import SearchKeywordsTool
from tabulaflow.core.formatters import SQLBasicSchemaFormatter, HSchemaFormatter
from tabulaflow.core.db_connector import SQLConnector
from tabulaflow.metadata_synthesizer import HSchemaSynthesizer
from tabulaflow.core.types import SQLSchema, HSQLSchema
from mcp.server.fastmcp import FastMCP


# os.environ["TABULAFLOW_SCHEMA_CACHE_ENABLED"] = "0"


mcp = FastMCP("postgres_financial", host="0.0.0.0", port=8126)


@dataclass
class GetSchemaTool:
    name: ClassVar[str] = "get_schema"
    schema: SQLSchema
    formatter: SQLBasicSchemaFormatter

    async def __call__(self):
        """Get the schema of the database."""
        return self.formatter.format(self.schema)


@dataclass
class GetHSchemaTool:
    name: ClassVar[str] = "get_hschema"
    hschema: HSQLSchema
    formatter: HSchemaFormatter

    async def __call__(self):
        """Get the schema of the database."""
        return self.formatter.format(self.hschema)


async def get_db_connector() -> SQLConnector:
    db_connector = await SQLConnector.from_url_async(
        global_id="blue+postgres_financial",
        url="postgresql+asyncpg://postgres:postgres@10.0.175.210:5440/financial",
        db_name="postgres_financial",
        enable_query_caching=True,
    )
    column_meaning_directory = "data/BIRD-SQL_column_meaning"
    with open(os.path.join(column_meaning_directory, "dev_column_meaning.json"), "r") as f:
        column_descriptions = {
            key.lower(): value.strip().strip("#").strip().replace("\n", " ") for key, value in json.load(f).items()
        }

    for table in db_connector.schema.tables:
        for column in table.columns:
            if column.name in (
                "a2",
                "a3",
                "a4",
                "a5",
                "a6",
                "a7",
                "a8",
                "a9",
                "a10",
                "a11",
                "a12",
                "a13",
                "a14",
                "a15",
                "a16",
            ):
                column.description = column.description = column_descriptions.get(
                    f"financial|{table.name}|{column.name}".lower(), None
                )

    return db_connector


async def main():
    db_connector = await get_db_connector()
    formatter = SQLBasicSchemaFormatter()
    get_schema_tool = GetSchemaTool(schema=db_connector.schema, formatter=formatter)
    run_query_tool = RunQueryTool(db_connector=db_connector)
    search_keywords_tool = SearchKeywordsTool(db_connector=db_connector)

    mcp.add_tool(get_schema_tool.__call__, name="get_schema")
    mcp.add_tool(run_query_tool.__call__, name="run_query")

    async def search_keywords(schema_name: str, table_name: str, column_name: str, keywords: list[str]) -> str:
        return await search_keywords_tool.__call__(schema_name, table_name, column_name, keywords)

    search_keywords.__doc__ = search_keywords_tool.__call__.__doc__
    mcp.add_tool(search_keywords, name="search_keywords")

    print(f"Started MCP server for database with the following schema:\n{await get_schema_tool()}")
    num_tables = len(db_connector.schema.tables)
    print(f"Number of tables: {num_tables}")
    num_columns = sum(len(table.columns) for table in db_connector.schema.tables)
    print(f"Number of columns: {num_columns}")


if __name__ == "__main__":
    asyncio.run(main())
    mcp.run(transport="streamable-http")
