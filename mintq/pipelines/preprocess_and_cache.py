import argparse
import os
import shutil
import time
from functools import reduce
import datetime
import asyncio
import logging
import litellm
import traceback
from tqdm.asyncio import tqdm_asyncio
from mintq import agent_registry, dataset_registry
from mintq.metrics import BaseMetricAggregator, SimpleInferenceMetricsAggregator
from mintq.preprocessors.base import BaseCachedDBPreprocessor, preprocessor_registry
from mintq.schema import NL2QDataset

logger = logging.getLogger(__name__)


async def preprocess_and_cache_async(
    dataset: NL2QDataset,
    preprocessors: list[BaseCachedDBPreprocessor],
    verbose: bool = True,
) -> None:
    for preprocessor in preprocessors:
        await tqdm_asyncio.gather(
            *[preprocessor.preprocess_async(db_connector) for db_connector in dataset.db_connectors.values()],
            disable=not verbose,
        )


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preprocessors", nargs="+", default=None)

    # dataset
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev_20240627")
    parser.add_argument("--databases", default=None, nargs="+")
    # parser.add_argument("--subsample_size", default=None, type=int)
    # parser.add_argument("--difficulty", default=None, choices=["simple", "moderate", "challenging"])
    # parser.add_argument("--include_taxonomy", action="store_true")

    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(databases=["california_schools"])
    args = parser.parse_args()
    print(args)
    print()

    preprocessor_names = args.preprocessors or preprocessor_registry.list_names()
    preprocessors = [preprocessor_registry.get_class(name)() for name in preprocessor_names]

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases from {args.dataset} ({args.split}) in {time.time() - t0:.2f} seconds."
    )

    t0 = time.time()
    await preprocess_and_cache_async(dataset, preprocessors)
    print(f"Finished preprocess and cache in {time.time() - t0:.2f} seconds.")


if __name__ == "__main__":
    asyncio.run(main_async())
