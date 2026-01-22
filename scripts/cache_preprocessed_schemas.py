import argparse
import time
import os
import asyncio
from mintq.datahub import dataset_registry
from mintq.metadata_synthesizers import SchemaPreprocessor


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

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    schema_preprocessor = SchemaPreprocessor()
    preprocessed_schemas = await asyncio.gather(
        *[schema_preprocessor.run_async(db_connector) for db_connector in dataset.db_connectors.values()]
    )
    print(f"Preprocessed {len(preprocessed_schemas)} schemas in {time.time() - t0:.2f} seconds.")

    usage = schema_preprocessor.usage()
    print(f"Total cost USD: {usage.api_cost_usd:.6f}")


if __name__ == "__main__":
    asyncio.run(main())
