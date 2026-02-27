import asyncio
import argparse
import os
import time
from mintq.config import config
from mintq.datahub import dataset_registry
from mintq.formatters import SQLDDLSchemaFormatter


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=config.default_dataset)
    parser.add_argument("--split", default=config.default_split)
    parser.add_argument("--database", default="european_football_2")
    parser.add_argument("--from_cache", action="store_true")
    args = parser.parse_args()
    if args.dataset == "bird-sql":
        parser.set_defaults(split="dev_20240627")
    elif args.dataset == "spider2-snow":
        parser.set_defaults(split="test")
    elif args.dataset == "beaver":
        parser.set_defaults(split="test")
    else:
        raise ValueError(f"Unknown dataset: {args.dataset}")

    print(args)
    print()

    if args.from_cache:
        os.environ["MINTQ_CACHE_ENABLED"] = "1"
        os.environ["MINTQ_CACHE_REQUIRED"] = "1"
    else:
        os.environ["MINTQ_CACHE_ENABLED"] = "0"
        os.environ["MINTQ_CACHE_REQUIRED"] = "0"

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=[args.database])
    schema = dataset.db_connectors[args.database].schema
    schema_str = SQLDDLSchemaFormatter().format(schema)
    print(schema_str)
    print()
    print(f"(schema length: {len(schema_str)} characters)")
    print()
    print(f"Time taken: {time.time() - t0} seconds")
    print(f"Tables: {[table.name for table in schema.tables]}")


if __name__ == "__main__":
    asyncio.run(main())
