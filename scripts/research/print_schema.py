import argparse
import asyncio
import time
from pathlib import Path
from typing import Any, Literal

from tabulaflow.core import SQLSchema
from tabulaflow.data import Neo4jConnectorConfig, SQLConnectorConfig
from tabulaflow.output.formatting import schema_formatter_registry
from tabulaflow.research.benchmarks import dataset_registry


async def main() -> None:
    parser = argparse.ArgumentParser(description="Print a database schema from a benchmark or cached SQL schema.")
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="Cached SQLSchema JSON file")
    source.add_argument("--database", help="Database name from the selected benchmark split")
    parser.add_argument("--formatter", default="sql_ddl")
    parser.add_argument("--no-compact-table-families", action="store_true")
    parser.add_argument("--no-description", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    started_at = time.perf_counter()
    if args.file is not None:
        schema = SQLSchema.model_validate_json(args.file.read_text())
    else:
        cache_mode: Literal["off", "read_write"] = "off" if args.no_cache else "read_write"
        config = (
            Neo4jConnectorConfig(schema_cache_mode=cache_mode)
            if args.dataset == "cypherbench"
            else SQLConnectorConfig(schema_cache_mode=cache_mode)
        )
        loader_class: Any = dataset_registry.get_class(args.dataset)
        loader = loader_class(connector_config=config)
        dataset = await loader.get_split_async(args.split, databases=[args.database])
        schema = dataset.db_connectors[args.database].schema

    formatter_kwargs = (
        {"compact_table_families": not args.no_compact_table_families} if isinstance(schema, SQLSchema) else {}
    )
    formatter_class: Any = schema_formatter_registry.get_class(args.formatter)
    formatter = formatter_class(**formatter_kwargs)
    rendered = formatter.format(schema, include_descriptions=not args.no_description)
    print(rendered)
    print()
    print(f"Schema length: {len(rendered)} characters")
    print(f"Tables: {[table.name for table in schema.tables]}")
    print(f"Elapsed: {time.perf_counter() - started_at:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
