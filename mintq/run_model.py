import argparse
import os
import shutil
import time
from typing import Callable
import datetime
import asyncio
import logfire
from functools import partial
import litellm
from tqdm import trange
from concurrent.futures import ThreadPoolExecutor
from mintq.utils import get_llm_api_cost, get_aggregated_metrics, format_trajectory, save_results
from mintq.schema_formatter import get_schema_formatter
from mintq.modelhub import get_nl2q_model_class, BaseNL2QModel, BaseAsyncNL2QModel
from mintq.datahub import get_dataset_loader
from mintq.schema import NL2QDataset, NL2QRunResult


logfire.configure(service_name="otel", send_to_logfire="if-token-present", console=False)
logfire.instrument_pydantic_ai()


def run_model_multi_threaded(
    model_fn: Callable[[], BaseNL2QModel], dataset: NL2QDataset, batch_size: int
) -> NL2QRunResult:
    start_time = datetime.datetime.now()
    tasks_with_predictions = []
    for i in trange(0, len(dataset.tasks), batch_size):
        j = min(i + batch_size, len(dataset.tasks))
        batch = dataset.tasks[i:j]

        nl2q_models = [model_fn() for _ in batch]

        with ThreadPoolExecutor(max_workers=len(batch)) as executor:
            futures = [
                executor.submit(
                    nl2q_model.predict_sync,
                    item,
                    dataset.db_connectors[item.db],
                )
                for item, nl2q_model in zip(batch, nl2q_models)
            ]
            tasks_with_predictions += [future.result() for future in futures]

        if i == 0:
            task = tasks_with_predictions[0]
            trajectory = task.trajectory if task.task_type == "simple" else task.trajectories[0]
            print(format_trajectory(trajectory))

    sample_model = model_fn()
    aggregated_metrics = get_aggregated_metrics([item.metrics for item in tasks_with_predictions])

    end_time = datetime.datetime.now()
    return NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=dataset.name,
        split_id=dataset.split_id,
        databases=dataset.databases,
        model=sample_model.name,
        model_args=sample_model.get_config(),
        aggregated_metrics=aggregated_metrics,
        tasks=tasks_with_predictions,
    )


async def run_model_async(
    model_fn: Callable[[], BaseAsyncNL2QModel], dataset: NL2QDataset, batch_size: int
) -> NL2QRunResult:
    start_time = datetime.datetime.now()
    tasks_with_predictions = []
    for i in trange(0, len(dataset.tasks), batch_size):
        j = min(i + batch_size, len(dataset.tasks))
        batch = dataset.tasks[i:j]

        tasks_with_predictions += await asyncio.gather(
            *[model_fn().predict_async(item, dataset.db_connectors[item.db]) for item in batch]
        )

        if i == 0:
            task = tasks_with_predictions[0]
            trajectory = task.trajectory if task.task_type == "simple" else task.trajectories[0]
            print(format_trajectory(trajectory))

    sample_model = model_fn()
    aggregated_metrics = get_aggregated_metrics([item.metrics for item in tasks_with_predictions])

    end_time = datetime.datetime.now()
    return NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=dataset.name,
        split_id=dataset.split_id,
        databases=dataset.databases,
        model=sample_model.name,
        model_args=sample_model.get_config(),
        aggregated_metrics=aggregated_metrics,
        tasks=tasks_with_predictions,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="sql_agent_table_names_only")
    parser.add_argument("-s", "--schema_formatter", default="sql_default")
    parser.add_argument("--llm", default="openai/gpt-4o")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("-n", "--num_majority_voting_candidates", default=1, type=int)
    parser.add_argument("--local_llm_config", default="local_llm_config.json")

    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", default=None, nargs="+")

    parser.add_argument("--batch_size", default=50, type=int)
    parser.add_argument("--result_dir", default="output/nl2q_simple_zero_shot_gpt-4o/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug_litellm", action="store_true")
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(batch_size=2, overwrite=True, result_dir="output/test/", split="dev")
        if args.dataset == "bird-sql":
            parser.set_defaults(databases=["california_schools"])
        elif args.dataset == "spider2-snow":
            parser.set_defaults(databases=["AIRLINES"])
    args = parser.parse_args()
    print(args)
    print()

    if args.debug_litellm:
        litellm._turn_on_debug()  # type: ignore

    if os.path.exists(args.result_dir):
        if not args.overwrite:
            print(f"{args.result_dir} already exists. Use --overwrite to overwrite the directory.")
            return
        else:
            shutil.rmtree(args.result_dir)
    os.makedirs(args.result_dir)

    if get_llm_api_cost(args.llm, 1000000, 1000000) == 0.0:
        print(f"Warning: LLM {args.llm} is not supported for API cost calculation.")

    # litellm_kwargs = {}
    # if args.llm.startswith("hosted_vllm/"):
    #     with open(args.local_llm_config, "r") as f:
    #         litellm_kwargs["api_base"] = json.load(f)[args.llm]["api_base"]
    schema_formatter = get_schema_formatter(args.schema_formatter)
    nl2q_kwargs = {
        "llm": args.llm,
        "temperature": args.temperature,
        "num_candidates": args.num_majority_voting_candidates,
        # "litellm_kwargs": litellm_kwargs,
        "schema_formatter": schema_formatter,
    }
    t0 = time.time()
    dataset_loader = get_dataset_loader(args.dataset)
    dataset = dataset_loader.get_split(args.split, databases=args.databases)
    if args.debug:
        dataset.tasks = dataset.tasks[:5]
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    model_class = get_nl2q_model_class(args.model)
    model_fn = partial(model_class, **nl2q_kwargs)
    sample_model = model_fn()
    if hasattr(sample_model, "predict_async"):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(run_model_async(model_fn, dataset, args.batch_size))  # type: ignore
    else:
        result = run_model_multi_threaded(model_fn, dataset, args.batch_size)  # type: ignore

    save_results(result, args.result_dir)


if __name__ == "__main__":
    main()
