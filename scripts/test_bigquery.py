#!/usr/bin/env -S uv run
"""Test BigQuery schema loading via Spider2LiteDatasetLoader."""

import asyncio
from tabulaflow.research.benchmarks.spider2_lite import Spider2LiteDatasetLoader
from tabulaflow.output.schema_formatters.sql_ddl import SQLDDLSchemaFormatter


async def main():
    loader = Spider2LiteDatasetLoader()
    connectors = await loader.get_db_connectors_async("test", databases=["ga4"])
    conn = connectors["ga4"]
    schema = conn.schema

    formatter = SQLDDLSchemaFormatter()
    formatted = formatter.format(schema, include_descriptions=True)

    with open("log/schema.out", "w") as f:
        f.write(formatted)
    print(f"Wrote {len(schema.tables)} tables to log/schema.out")


if __name__ == "__main__":
    asyncio.run(main())
