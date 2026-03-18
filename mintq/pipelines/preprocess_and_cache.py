import argparse
import collections
import time
import asyncio
import os
import logging
from typing import Any
from tqdm.asyncio import tqdm_asyncio
from mintq import dataset_registry
import mintq
from mintq.preprocessors.base import NL2QPreprocessor, preprocessor_registry
from mintq.config import mintq_config
from mintq.schema import NL2QDataset

logger = logging.getLogger(__name__)


async def preprocess_and_cache_async(
    dataset: NL2QDataset,
    preprocessors: list[NL2QPreprocessor],
    verbose: bool = True,
) -> None:
    for preprocessor in preprocessors:
        if verbose:
            print(f"Caching {preprocessor.name} results...")
        if preprocessor.input_type == "db_connector":
            await tqdm_asyncio.gather(
                *[preprocessor.preprocess_async(db_connector) for db_connector in dataset.db_connectors.values()],
                disable=not verbose,
            )
        elif preprocessor.input_type == "dataset":
            await preprocessor.preprocess_async(dataset)
        else:
            raise ValueError(f"Unknown input type: {preprocessor.input_type}")


def parse_preprocessor_args(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    all_preprocessor_args: dict[str, dict[str, Any]] = collections.defaultdict(dict)
    if args.schema_preprocessor_column_profiler_llm is not None:
        all_preprocessor_args["schema_preprocessor"]["column_profiler_llm"] = (
            args.schema_preprocessor_column_profiler_llm
        )
    if args.schema_preprocessor_foreign_key_predictor_llm is not None:
        all_preprocessor_args["schema_preprocessor"]["foreign_key_predictor_llm"] = (
            args.schema_preprocessor_foreign_key_predictor_llm
        )
    if args.question_embedder_embedding_llm is not None:
        all_preprocessor_args["question_embedder"]["embedding_llm"] = args.question_embedder_embedding_llm
    if args.db_summarizer_llm is not None:
        all_preprocessor_args["db_summarizer"]["llm"] = args.db_summarizer_llm
    return all_preprocessor_args


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no_preprocessing", action="store_true")
    parser.add_argument(
        "--preprocessors", nargs="+", default=["schema_preprocessor", "er_diagram_synthesizer", "db_summarizer"]
    )

    # dataset
    parser.add_argument("--dataset", default=mintq_config.dataset)
    parser.add_argument("--split", default=mintq_config.split)
    parser.add_argument("--databases", default=None, nargs="+")

    # preprocessor configs
    parser.add_argument("--schema_preprocessor_column_profiler_llm", default=None)
    parser.add_argument("--schema_preprocessor_foreign_key_predictor_llm", default=None)
    parser.add_argument("--question_embedder_embedding_llm", default=None)
    parser.add_argument("--db_summarizer_llm", default=None)

    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.dataset == "bird-sql":
        parser.set_defaults(
            split="dev", preprocessors=["schema_preprocessor", "er_diagram_synthesizer", "db_summarizer"]
        )
    elif args.dataset == "spider2-snow":
        parser.set_defaults(
            split="test", preprocessors=["schema_preprocessor", "er_diagram_synthesizer", "db_summarizer"]
        )

    if args.debug:
        parser.set_defaults(databases=["california_schools"])

    if args.overwrite:
        os.environ["MINTQ_PREPROCESSOR_CACHE_OVERWRITE"] = "1"

    args = parser.parse_args()
    print(args)
    print()

    mintq.configure()

    os.environ["MINTQ_PREPROCESSOR_CACHE_ENABLED"] = "1"
    os.environ["MINTQ_PREPROCESSOR_CACHE_REQUIRED"] = "0"
    mintq_config.reload_from_env()

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases from {args.dataset} ({args.split}) in {time.time() - t0:.2f} seconds."
    )

    if args.no_preprocessing:
        print("Skipping preprocessing and caching because --no_preprocessing was set.")
        return

    preprocessor_names = args.preprocessors or preprocessor_registry.list_names()
    all_preprocessor_args = parse_preprocessor_args(args)
    preprocessors = [
        preprocessor_registry.get_class(name)(**all_preprocessor_args.get(name, {})) for name in preprocessor_names
    ]

    t0 = time.time()
    await preprocess_and_cache_async(dataset, preprocessors)
    print(f"Finished preprocess and cache in {time.time() - t0:.2f} seconds.")

    print()
    print("Preprocessor usage:")
    for preprocessor in preprocessors:
        usage = preprocessor.usage()
        if usage is None:
            print(f"- {preprocessor.name}: N/A")
        else:
            print(f"- {preprocessor.name}: {usage.api_cost_usd:.6f} USD")


if __name__ == "__main__":
    asyncio.run(main_async())
