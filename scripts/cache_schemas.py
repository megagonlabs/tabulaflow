import argparse
import time
import os
import asyncio
from mintq.datahub import dataset_registry
from mintq.config import mintq_config


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=mintq_config.dataset)
    parser.add_argument("--split", default=mintq_config.split)
    parser.add_argument("--databases", default=None, nargs="+")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    mintq_config.setup_logging()

    os.environ["MINTQ_SCHEMA_CACHE_ENABLED"] = "1"
    os.environ["MINTQ_SCHEMA_CACHE_REQUIRED"] = "0"
    if args.overwrite:
        os.environ["MINTQ_SCHEMA_CACHE_OVERWRITE"] = "1"
    else:
        os.environ["MINTQ_SCHEMA_CACHE_OVERWRITE"] = "0"
    mintq_config.reload_from_env()

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )


if __name__ == "__main__":
    asyncio.run(main())
