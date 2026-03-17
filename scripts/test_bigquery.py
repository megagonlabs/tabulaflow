#!/usr/bin/env -S uv run
"""Test BigQuery schema loading via Spider2LiteDatasetLoader."""

import asyncio
from mintq.datahub.spider2_lite import Spider2LiteDatasetLoader
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter


async def main():
    loader = Spider2LiteDatasetLoader()
    connectors = await loader.get_db_connectors_async("test", databases=["ga4"])
    conn = connectors["ga4"]
    schema = conn.schema

    formatter = SQLDDLSchemaFormatter()
    formatted = formatter.format(schema, add_description=True)

    with open("log/schema.out", "w") as f:
        f.write(formatted)
    print(f"Wrote {len(schema.tables)} tables to log/schema.out")


if __name__ == "__main__":
    asyncio.run(main())
