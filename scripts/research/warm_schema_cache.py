import argparse
import asyncio
import time
from typing import Any, Literal

from tabulaflow.data import Neo4jConnectorConfig, SQLConnectorConfig
from tabulaflow.research.benchmarks import dataset_registry


async def main() -> None:
    parser = argparse.ArgumentParser(description="Populate schema caches for a benchmark split.")
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", nargs="+")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    started_at = time.perf_counter()
    cache_mode: Literal["refresh", "read_write"] = "refresh" if args.refresh else "read_write"
    config = (
        Neo4jConnectorConfig(schema_cache_mode=cache_mode)
        if args.dataset == "cypherbench"
        else SQLConnectorConfig(schema_cache_mode=cache_mode)
    )
    loader_class: Any = dataset_registry.get_class(args.dataset)
    loader = loader_class(connector_config=config)
    dataset = await loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases "
        f"from {args.dataset} {args.split} in {time.perf_counter() - started_at:.2f} seconds"
    )


if __name__ == "__main__":
    asyncio.run(main())
