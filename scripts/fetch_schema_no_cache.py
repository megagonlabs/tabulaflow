import asyncio
import argparse
import os
import time
from mintq.datahub import dataset_registry
from mintq.formatters import SQLDefaultSchemaFormatter


os.environ["MINTQ_CACHE_ENABLED"] = "0"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--database", default="european_football_2")
    parser.add_argument("--enable_cache", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    if args.enable_cache:
        os.environ["MINTQ_CACHE_ENABLED"] = "1"

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=[args.database])
    schema = dataset.db_connectors[args.database].schema
    print(SQLDefaultSchemaFormatter().format(schema))
    print()
    print(f"Time taken: {time.time() - t0} seconds")
    print(f"Tables: {[table.name for table in schema.tables]}")


if __name__ == "__main__":
    asyncio.run(main())
