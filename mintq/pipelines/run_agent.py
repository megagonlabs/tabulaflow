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
from tqdm import trange
from mintq import agent_registry, dataset_registry
from mintq.metrics import BaseMetricAggregator, SimpleInferenceMetricsAggregator
from mintq.utils import pprint_dict
from mintq.agenthub import NL2QAgent, BaseAgentConfig
from mintq.agenthub.user_simulator import UserSimulator
from mintq.schema import (
    NL2QDataset,
    NL2QRunResult,
    NL2QTask,
    NL2QTaskOutput,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    Usage,
)

logger = logging.getLogger(__name__)


def get_empty_output(agent_cls: type[NL2QAgent], task: NL2QTask) -> NL2QTaskOutput:
    if agent_cls.output_type == "simple":
        return SimpleNL2QTaskOutput(**task.model_dump(), pred_query=None)
    elif agent_cls.output_type == "ambig-simple":
        return SimpleAmbigNL2QTaskOutput(**task.model_dump(), pred_intended_query=None)
    elif agent_cls.output_type == "ambig-flat":
        return FlatAmbigNL2QTaskOutput(
            **task.model_dump(), interpretations=[], parameters=[], pred_queries=[], pred_intended_query_id=None
        )
    elif agent_cls.output_type == "ambig-structured":
        return StructuredAmbigNL2QTaskOutput(
            **task.model_dump(), pred_ambiguity_points=[], pred_queries=[], pred_intended_query_id=None
        )
    else:
        raise ValueError(f"Unknown agent output type: {agent_cls.output_type}")


async def run_agent_async(
    agent_cls: type[NL2QAgent],
    agent_config: BaseAgentConfig,
    dataset: NL2QDataset,
    batch_size: int,
    metric_aggregators: list[BaseMetricAggregator] = [SimpleInferenceMetricsAggregator()],
    sleep_between_batches: float = 0.0,
    verbose: bool = False,
) -> NL2QRunResult:
    start_time = datetime.datetime.now()
    task_outputs = []
    num_failed = 0
    for i in trange(0, len(dataset.tasks), batch_size):
        if sleep_between_batches > 0:
            time.sleep(sleep_between_batches)

        j = min(i + batch_size, len(dataset.tasks))
        batch = dataset.tasks[i:j]

        batch_kwargs = []
        for task in batch:
            if task.task_type != agent_cls.task_type:
                raise ValueError(
                    f"Task type {task.task_type} does not match agent requiredtask type {agent_cls.task_type}"
                )

            if task.task_type == "ambig":
                user_simulator = UserSimulator.from_ambig_nl2q_task(
                    task,
                    include_history=agent_cls.name == "ambig_simple_sql_agent",
                    answer_with_multiple_ambig_points=agent_cls.name == "ambig_flat_sql_agent",
                )
                batch_kwargs.append({"user_simulator": user_simulator})
            else:
                batch_kwargs.append({})

        agents: list[NL2QAgent] = await asyncio.gather(*[agent_cls.from_config_async(agent_config) for _ in batch])  # type: ignore
        batch_outputs = await asyncio.gather(
            *[
                agent.predict_async(task, dataset.db_connectors[task.db], **kwargs)  # type: ignore
                for agent, task, kwargs in zip(agents, batch, batch_kwargs)
            ],
            return_exceptions=True,
        )
        for task, output in zip(batch, batch_outputs):
            if isinstance(output, Exception):
                tb_str = "".join(traceback.format_exception(type(output), output, output.__traceback__))
                logger.error(f"Error running agent {agent_cls.name} for task {task.qid}: {tb_str}")
                task_outputs.append(get_empty_output(agent_cls, task))
                num_failed += 1
            elif isinstance(output, BaseException):
                raise output
            else:
                task_outputs.append(output)

        if i == 0 and verbose:
            trajectory = getattr(task_outputs[0], "trajectory", None)
            if trajectory:
                for tr in trajectory if isinstance(trajectory, list) else [trajectory]:
                    print(tr.to_readable())

        if verbose:
            print(f"{len(task_outputs)}/{len(dataset.tasks)} tasks completed ({num_failed} failed)")

    end_time = datetime.datetime.now()

    usages = [t.usage for t in task_outputs if t.usage is not None]
    user_simulator_usages = [
        t.user_simulator_usage for t in task_outputs if t.task_type == "ambig" and t.user_simulator_usage
    ]

    res = NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=dataset.name,
        split=dataset.split,
        subsample_size=dataset.subsample_size,
        databases=dataset.databases,
        agent=agent_cls.name,
        agent_config=agent_config.model_dump(),
        total_usage=reduce(lambda x, y: x + y, usages) if usages else None,
        total_user_simulator_usage=reduce(lambda x, y: x + y, user_simulator_usages) if user_simulator_usages else None,
        aggregated_inference_metrics={},
        tasks=task_outputs,
    )
    for aggregator in metric_aggregators:
        res.aggregated_inference_metrics.update(aggregator.aggregate(res))
    return res


def parse_agent_config(agent_cls: type[NL2QAgent], args: argparse.Namespace) -> BaseAgentConfig:
    kwargs = {
        "llm": args.llm,
        "schema_formatter": args.schema_formatter,
        "temperature": args.temperature,
    }
    if agent_cls.name == "simple_zero_shot":
        kwargs["num_candidates"] = args.num_majority_voting_candidates
    if args.no_query_for_intended_only:
        kwargs["query_for_intended_only"] = False
    if args.use_gold_phrases:
        kwargs["use_gold_phrases"] = True
    if args.use_gold_ambiguity_points:
        kwargs["use_gold_ambiguity_points"] = True
    if args.user_patience is not None:
        kwargs["user_patience"] = args.user_patience
    if args.openai_reasoning_effort is not None:
        kwargs["openai_reasoning_effort"] = args.openai_reasoning_effort
    if args.openai_reasoning_summary is not None:
        kwargs["openai_reasoning_summary"] = args.openai_reasoning_summary
    return agent_cls.config_cls(**kwargs)


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="sql_agent")
    parser.add_argument("-s", "--schema_formatter", default="sql_default")
    parser.add_argument("--llm", default="openai-responses:gpt-4.1")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("--openai_reasoning_effort", default=None)
    parser.add_argument("--openai_reasoning_summary", default=None)
    parser.add_argument("-n", "--num_majority_voting_candidates", default=1, type=int)

    # ambig agents
    parser.add_argument("--no_query_for_intended_only", action="store_true")
    parser.add_argument("--use_gold_phrases", action="store_true")
    parser.add_argument("--use_gold_ambiguity_points", action="store_true")
    parser.add_argument("--user_patience", default=None)

    parser.add_argument("--dataset", default="arcs")
    parser.add_argument("--split", default="test")
    parser.add_argument("--databases", default=None, nargs="+")
    parser.add_argument("--subsample_size", default=None, type=int)
    parser.add_argument("--include_taxonomy", action="store_true")

    parser.add_argument("--batch_size", default=8, type=int)
    parser.add_argument("--sleep_between_batches", default=0.0, type=float)
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug_litellm", action="store_true")
    parser.add_argument("--log_level", default="WARNING", type=str)
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(batch_size=2, overwrite=True, result_dir="output/test/", split="test")
        if args.dataset == "bird-sql":
            parser.set_defaults(databases=["california_schools"], split="dev")
        elif args.dataset == "spider2-snow":
            parser.set_defaults(databases=["AIRLINES"])
    args = parser.parse_args()
    print(args)
    print()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    if args.debug_litellm:
        litellm._turn_on_debug()  # type: ignore

    if os.path.exists(args.result_dir):
        if not args.overwrite:
            print(f"{args.result_dir} already exists. Use --overwrite to overwrite the directory.")
            return
        else:
            shutil.rmtree(args.result_dir)
    os.makedirs(args.result_dir)

    if Usage.create(args.llm, 1, 1000000, 1000000).api_cost_usd == 0:
        print(f"Warning: API cost for {args.llm} is 0.0. API cost calculation might not be supported for {args.llm}.")

    t0 = time.time()
    dataset_kwargs = {}
    if args.include_taxonomy:
        dataset_kwargs["include_taxonomy"] = True
    dataset_loader = dataset_registry.get_class(args.dataset)(**dataset_kwargs)
    dataset = await dataset_loader.get_split_async(
        args.split, databases=args.databases, subsample_size=args.subsample_size
    )
    if args.debug:
        if args.dataset == "arcs":
            # dataset.tasks = dataset.tasks[10:13]
            dataset.tasks = [
                task
                for task in dataset.tasks
                if task.qid in ["040-0", "001-0", "001-1", "001-2", "001-3", "001-4", "046-5"]
            ]
        else:
            dataset.tasks = dataset.tasks[:5]
    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases from {args.dataset} ({args.split}) in {time.time() - t0:.2f} seconds."
    )

    agent_class = agent_registry.get_class(args.agent)
    config = parse_agent_config(agent_class, args)
    print(f"Running agent {agent_class.name} with config:")
    print(config.model_dump_json(indent=2))

    t0 = time.time()
    result = await run_agent_async(agent_class, config, dataset, args.batch_size, verbose=True)
    print()
    print(f"Ran on {len(dataset.tasks)} tasks in {time.time() - t0:.2f} seconds.")
    agent_cost = "N/A" if result.total_usage is None else f"{result.total_usage.api_cost_usd:.6f}"
    user_simulator_cost = (
        "N/A" if result.total_user_simulator_usage is None else f"{result.total_user_simulator_usage.api_cost_usd:.6f}"
    )
    print(f"Total cost USD (agent): {agent_cost}")
    print(f"Total cost USD (user simulator): {user_simulator_cost}")
    if "user_effort" in result.aggregated_inference_metrics:
        user_effort = result.aggregated_inference_metrics["user_effort"]["avg"]
        print(f"Avg user effort: {user_effort:.2f}")

    result.to_directory(args.result_dir)
    print()
    print(f"Saved result to {args.result_dir}")

    print()
    print("Aggregated inference metrics:")
    print(pprint_dict(result.aggregated_inference_metrics))


if __name__ == "__main__":
    asyncio.run(main_async())
