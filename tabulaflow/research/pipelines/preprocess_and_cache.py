import argparse
import collections
import time
import asyncio
import logging
from typing import Any
from tqdm.asyncio import tqdm_asyncio
from tabulaflow.research.benchmarks.registry import dataset_registry
from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime
from tabulaflow.research.preprocessing.registry import preprocessor_registry
from tabulaflow.research.observability import configure_research_observability
from tabulaflow.research.types import NL2QDataset


async def preprocess_and_cache_async(
    dataset: NL2QDataset,
    preprocessors: list[Any],
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
    parser.add_argument(
        "--preprocessors", nargs="+", default=["schema_preprocessor", "er_diagram_synthesizer", "db_summarizer"]
    )

    # dataset
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default=None)
    parser.add_argument("--databases", default=None, nargs="+")

    # preprocessor configs
    parser.add_argument("--schema-preprocessor-column-profiler-llm", default=None)
    parser.add_argument("--schema-preprocessor-foreign-key-predictor-llm", default=None)
    parser.add_argument("--question-embedder-embedding-llm", default=None)
    parser.add_argument("--db-summarizer-llm", default=None)

    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--log-level", type=str.upper, choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="WARNING")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    if args.split is None:
        args.split = "test" if args.dataset == "spider2-snow" else "dev"
    print(args)
    print()

    initialize_agent_runtime(AgentRuntimeConfig(preprocessing_cache_mode="refresh" if args.overwrite else "read_write"))
    configure_research_observability()

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases from {args.dataset} ({args.split}) in {time.time() - t0:.2f} seconds."
    )

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
