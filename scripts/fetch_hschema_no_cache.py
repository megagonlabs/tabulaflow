import asyncio
import argparse
import os
import time
from mintq.datahub import dataset_registry
from mintq.formatters import HSchemaFormatter
from mintq.metadata_synthesizer import HSchemaSynthesizer


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--database", default="european_football_2")
    parser.add_argument("--enable_cache", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=[args.database])
    db_connector = dataset.db_connectors[args.database]
    print(f"Database loaded in {time.time() - t0} seconds")

    os.environ["MINTQ_CACHE_ENABLED"] = "0"
    if args.enable_cache:
        os.environ["MINTQ_CACHE_ENABLED"] = "1"
    t0 = time.time()
    hschema = await HSchemaSynthesizer().run_async(db_connector)
    print(f"HSchema synthesized in {time.time() - t0} seconds")
    print(HSchemaFormatter().format(hschema))
    print()
    print(f"Table groups: {[tg.name for tg in hschema.table_groups]}")


if __name__ == "__main__":
    asyncio.run(main())
