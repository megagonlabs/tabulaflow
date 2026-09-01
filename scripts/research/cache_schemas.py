import argparse
import time
import asyncio
from tabulaflow.research.benchmarks import dataset_registry
from tabulaflow.data import Neo4jConnectorConfig, SQLConnectorConfig


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", default=None, nargs="+")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    t0 = time.time()
    config = (
        Neo4jConnectorConfig(schema_cache_mode="refresh" if args.overwrite else "read_write")
        if args.dataset == "cypherbench"
        else SQLConnectorConfig(schema_cache_mode="refresh" if args.overwrite else "read_write")
    )
    dataset_loader = dataset_registry.get_class(args.dataset)(connector_config=config)  # type: ignore[call-arg]
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )


if __name__ == "__main__":
    asyncio.run(main())
