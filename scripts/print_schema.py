import asyncio
import argparse
import time
from tabulaflow.research.benchmarks import dataset_registry
from tabulaflow.output.schema_formatters import schema_formatter_registry
from tabulaflow.core import SQLSchema
from tabulaflow.output.schema_compression import SchemaCompressor
from tabulaflow.data import Neo4jConnectorConfig, SQLConnectorConfig


async def main() -> None:
    parser = argparse.ArgumentParser(description="Print a database schema from a dataset or a cached JSON file.")

    # Source: either --file or --dataset + --database
    parser.add_argument("--dataset", default="bird-sql", help="Dataset name (e.g. bird-sql, spider2-snow, beaver)")
    parser.add_argument("--split", default="dev", help="Dataset split (auto-detected if omitted)")
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--file", help="Path to a cached schema JSON file (e.g. cache/schemas/spider2-snow+NOAA_DATA.json)"
    )
    source.add_argument("--database", default=None, help="Database name (required when using --dataset)")
    parser.add_argument("--formatter", default="sql_ddl", help="Schema formatter (default: sql_ddl)")
    parser.add_argument("--no_compress", action="store_true", help="Do not compress schema before formatting")
    parser.add_argument("--no_description", action="store_true", help="Omit column descriptions")
    parser.add_argument("--no_cache", action="store_true", help="Do not load schema from cache")
    args = parser.parse_args()

    if not args.file and not args.database:
        parser.error("--file or --database is required")
    if args.database and not args.dataset:
        parser.error("--dataset is required when using --database")

    print(args)
    print()

    t0 = time.time()

    if args.file:
        with open(args.file, "r") as f:
            schema = SQLSchema.model_validate_json(f.read())
    else:
        # Resolve split
        split = args.split
        if split is None:
            default_splits = {"bird-sql": "dev", "spider2-snow": "test", "beaver": "test"}
            split = default_splits.get(args.dataset, "dev")

        config = (
            Neo4jConnectorConfig(schema_cache_mode="off" if args.no_cache else "read_write")
            if args.dataset == "cypherbench"
            else SQLConnectorConfig(schema_cache_mode="off" if args.no_cache else "read_write")
        )
        dataset_loader = dataset_registry.get_class(args.dataset)(connector_config=config)  # type: ignore[call-arg]
        dataset = await dataset_loader.get_split_async(split, databases=[args.database])
        schema = dataset.db_connectors[args.database].schema

    if not args.no_compress:
        schema = SchemaCompressor().compress(schema)

    formatter = schema_formatter_registry.get_class(args.formatter)()
    schema_str = formatter.format(schema, include_descriptions=not args.no_description)
    print(schema_str)
    print()
    print(f"(schema length: {len(schema_str)} characters)")
    print(f"Tables: {[table.name for table in schema.tables]}")
    print(f"Time taken: {time.time() - t0:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
