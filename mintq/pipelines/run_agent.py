import argparse
import os
import shutil
import time
from typing import Type, Any
import datetime
import asyncio
import logfire
import litellm
from tqdm import trange
from mintq.utils import avg_and_round
from mintq.formatters import get_schema_formatter
from mintq.agenthub import get_nl2q_agent_class, BaseAsyncNL2QAgent
from mintq.datahub import get_dataset_loader
from mintq.agenthub.user_simulator import UserSimulator
from mintq.schema import NL2QDataset, NL2QRunResult, Usage


logfire.configure(service_name="otel", send_to_logfire="if-token-present", console=False)
logfire.instrument_pydantic_ai()


async def run_agent_async(
    agent_cls: Type[BaseAsyncNL2QAgent], agent_args: dict[str, Any], dataset: NL2QDataset, batch_size: int
) -> NL2QRunResult:
    start_time = datetime.datetime.now()
    task_outputs = []
    for i in trange(0, len(dataset.tasks), batch_size):
        j = min(i + batch_size, len(dataset.tasks))
        batch = dataset.tasks[i:j]

        batch_kwargs = []
        for task in batch:
            if task.task_type == "ambig":
                batch_kwargs.append({"user_simulator": UserSimulator.from_ambig_nl2q_task(task)})
            else:
                batch_kwargs.append({})

        task_outputs += await asyncio.gather(
            *[
                agent_cls(**agent_args).predict_async(task, dataset.db_connectors[task.db], **kwargs)
                for task, kwargs in zip(batch, batch_kwargs)
            ]
        )

        if i == 0:
            if getattr(task_outputs[0], "trajectory", None):
                print(task_outputs[0].trajectory.to_readable())  # type: ignore

    sample_agent = agent_cls(**agent_args)
    aggregated_metrics = {}
    aggregated_metrics["avg_latency_seconds"] = avg_and_round([task.metrics["latency_seconds"] for task in task_outputs])
    aggregated_metrics["avg_steps"] = avg_and_round([task.metrics["steps"] for task in task_outputs])
    aggregated_metrics["total_api_calls"] = sum([sum(usage.api_calls for usage in task.usages) for task in task_outputs])
    aggregated_metrics["total_input_tokens"] = sum([sum(usage.input_tokens for usage in task.usages) for task in task_outputs])
    aggregated_metrics["total_output_tokens"] = sum([sum(usage.output_tokens for usage in task.usages) for task in task_outputs])
    aggregated_metrics["avg_api_cost_usd"] = avg_and_round([sum(usage.api_cost_usd for usage in task.usages) for task in task_outputs], 4)
    aggregated_metrics["total_api_cost_usd"] = round(sum([usage.api_cost_usd for task in task_outputs for usage in task.usages]), 4)

    end_time = datetime.datetime.now()
    return NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=dataset.name,
        split=dataset.split,
        subsample_size=dataset.subsample_size,
        databases=dataset.databases,
        agent=sample_agent.name,
        agent_args=sample_agent.get_config(),
        aggregated_metrics=aggregated_metrics,
        tasks=task_outputs,
    )


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="sql_agent")
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

    if Usage.get_llm_api_cost(args.llm, 1000000, 1000000) == 0.0:
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
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    if args.debug:
        dataset.tasks = dataset.tasks[:5]
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    agent_class = get_nl2q_agent_class(args.agent)
    result = await run_agent_async(agent_class, nl2q_kwargs, dataset, args.batch_size)
    result.to_directory(args.result_dir)
    print(f"Saved result to {args.result_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
