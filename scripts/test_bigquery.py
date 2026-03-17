#!/usr/bin/env -S uv run
"""Test BigQuery schema loading via Spider2LiteDatasetLoader."""

import asyncio
from mintq.datahub.spider2_lite import Spider2LiteDatasetLoader


async def main():
    loader = Spider2LiteDatasetLoader()
    connectors = await loader.get_db_connectors_async("test", databases=["austin"])
    conn = connectors["austin"]
    schema = conn.schema
    print(f"Database: {schema.name}")
    print(f"Tables: {len(schema.tables)}")
    for table in schema.tables:
        col_names = [c.name for c in table.columns]
        print(f"  {table.schema_name}.{table.name} ({len(table.columns)} cols): {col_names[:5]}...")


if __name__ == "__main__":
    asyncio.run(main())
