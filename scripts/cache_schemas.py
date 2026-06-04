import argparse
import time
import asyncio
from tabulaflow.datahub import dataset_registry
import tabulaflow


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", default=None, nargs="+")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    tabulaflow.configure(
        schema_cache_enabled=True,
        schema_cache_required=False,
        schema_cache_overwrite=args.overwrite,
    )

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )


if __name__ == "__main__":
    asyncio.run(main())
