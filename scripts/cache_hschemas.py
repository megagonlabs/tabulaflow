import argparse
import time
import os
import asyncio
from mintq.datahub import get_dataset_loader
from mintq.metadata_synthesizer import HSchemaSynthesizer


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="spider2-snow")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", default=None, nargs="+")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    os.environ["MINTQ_CACHE_ENABLED"] = "1"
    if args.overwrite:
        os.environ["MINTQ_CACHE_REFRESH"] = "1"
    else:
        os.environ["MINTQ_CACHE_REFRESH"] = "0"

    # os.environ["MINTQ_CACHE_ENABLED"] = "0"

    t0 = time.time()
    dataset_loader = get_dataset_loader(args.dataset)
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    t0 = time.time()
    asyncio.gather(*[HSchemaSynthesizer().run_async(db_connector) for db_connector in dataset.db_connectors.values()])
    print(f"Cached {len(dataset.db_connectors)} hschemas in {time.time() - t0:.2f} seconds.")


if __name__ == "__main__":
    asyncio.run(main())
