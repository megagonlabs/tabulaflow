import argparse
from dataclasses import dataclass
from typing import ClassVar
import asyncio
import os
import json
from mintq.toolhub import RunQueryTool, SearchKeywordsTool
from mintq.formatters import SQLDefaultSchemaFormatter, HSchemaFormatter
from mintq.db_connector import SQLConnector
from mintq.metadata_synthesizer import HSchemaSynthesizer
from mintq.schema import SQLSchema, HSQLSchema
from mcp.server.fastmcp import FastMCP


# os.environ["MINTQ_CACHE_ENABLED"] = "0"


mcp = FastMCP("postgres_github_repos", host="0.0.0.0", port=8127)


@dataclass
class GetSchemaTool:
    name: ClassVar[str] = "get_schema"
    schema: SQLSchema
    formatter: SQLDefaultSchemaFormatter

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
        global_id="blue+postgres_github_repos",
        db_name="postgres_github_repos",
        engine_type="async",
        url="postgresql+asyncpg://postgres:postgres@10.0.175.210:5441/github_repos",
    )
    return db_connector


async def main():
    db_connector = await get_db_connector()
    hschema_synthesizer = HSchemaSynthesizer()
    hschema = await hschema_synthesizer.run_async(db_connector)
    formatter = HSchemaFormatter()
    get_schema_tool = GetHSchemaTool(hschema=hschema, formatter=formatter)
    run_query_tool = RunQueryTool(db_connector=db_connector)
    search_keywords_tool = SearchKeywordsTool(db_connector=db_connector)

    mcp.add_tool(get_schema_tool.__call__, name="get_schema")
    mcp.add_tool(run_query_tool.__call__, name="run_query")
    mcp.add_tool(search_keywords_tool.__call__, name="search_keywords")

    print(f"Started MCP server for database with the following schema:\n{await get_schema_tool()}")


if __name__ == "__main__":
    asyncio.run(main())
    mcp.run(transport="streamable-http")
