import argparse
from dataclasses import dataclass
from typing import ClassVar
import asyncio
import os
import json
from tabulaflow.toolhub import RunQueryTool, SearchKeywordsTool
from tabulaflow.formatters import SQLBasicSchemaFormatter, HSchemaFormatter
from tabulaflow.db_connector import SQLConnector
from tabulaflow.metadata_synthesizer import HSchemaSynthesizer
from tabulaflow.schema import SQLSchema, HSQLSchema
from mcp.server.fastmcp import FastMCP


# os.environ["TABULAFLOW_SCHEMA_CACHE_ENABLED"] = "0"


mcp = FastMCP("postgres_example_hr_matching_curation", host="0.0.0.0", port=8125)


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
        global_id="blue+postgres_example_hr_matching_curation",
        url="postgresql+asyncpg://postgres:postgres@10.0.171.151:5432/hr_matching_curation",
        db_name="postgres_example_hr_matching_curation",
        enable_query_caching=True,
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
