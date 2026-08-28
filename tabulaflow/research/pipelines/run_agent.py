import argparse
import os
import shutil
import time
from functools import reduce
from typing import Any
import datetime
import asyncio
import logging
import traceback
from tabulaflow.research.agents.registry import agent_registry
from tabulaflow.research.benchmarks.registry import dataset_registry
from tabulaflow.research.metrics import MetricAggregator, SimpleInferenceMetricsAggregator
from tabulaflow.research.pipelines.utils import pprint_dict, tqdm_gather_with_exceptions
from tabulaflow.research.observability import configure_research_observability
from tabulaflow.research.pipelines.utils import bool_flag
from tabulaflow.research.agents import NL2QAgent, AgentConfig
from tabulaflow.research.agents.user_simulator import UserSimulator
from tabulaflow.research.benchmarks.spider2_dbt import prepare_working_env_async
from tabulaflow.agents.trace import Usage
from tabulaflow.research.types import (
    NL2QDataset,
    NL2QRunResult,
    NL2QTask,
    NL2QTaskOutput,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    DbtTaskOutput,
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
    elif agent_cls.output_type == "dbt":
        return DbtTaskOutput(**task.model_dump())
    else:
        raise ValueError(f"Unknown agent output type: {agent_cls.output_type}")


async def run_agent_async(
    agent_cls: type[NL2QAgent],
    agent_config: AgentConfig,
    dataset: NL2QDataset,
    batch_size: int,
    few_shot_dataset: NL2QDataset | None = None,
    result_dir: str = "output/test/",
    metric_aggregators: list[MetricAggregator] | None = None,
    sleep_between_batches: float = 0.0,
    verbose: bool = True,
) -> NL2QRunResult:
    if metric_aggregators is None:
        metric_aggregators = [SimpleInferenceMetricsAggregator()]
    if hasattr(agent_config, "llm") and Usage.create(agent_config.llm, 1, 1000000, 1000000).api_cost_usd == 0:
        logger.warning("API cost for %s is 0.0. Cost calculation might not be supported.", agent_config.llm)

    if dataset.name == "spider2-dbt":
        await prepare_working_env_async(dataset, result_dir)

    start_time = datetime.datetime.now()
    task_outputs = []
    num_failed = 0
    for i in range(0, len(dataset.tasks), batch_size):
        if sleep_between_batches > 0:
            await asyncio.sleep(sleep_between_batches)

        j = min(i + batch_size, len(dataset.tasks))
        batch = dataset.tasks[i:j]

        agent_kwargs = {}
        if few_shot_dataset is not None:
            agent_kwargs["few_shot_dataset"] = few_shot_dataset
        agents: list[NL2QAgent] = await asyncio.gather(
            *[agent_cls.from_config_async(agent_config, **agent_kwargs) for _ in batch]  # type: ignore
        )

        batch_kwargs: list[dict[str, Any]] = []
        for task in batch:
            if task.task_type != agent_cls.task_type:
                raise ValueError(
                    f"Task type {task.task_type} does not match agent required task type {agent_cls.task_type}"
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

        batch_outputs = await tqdm_gather_with_exceptions(
            *[
                agent.predict_async(task, dataset.db_connectors[task.db], **kwargs)  # type: ignore
                for agent, task, kwargs in zip(agents, batch, batch_kwargs)
            ],
            return_exceptions=True,
            disable=not verbose,
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

        if verbose:
            print(f"{j}/{len(dataset.tasks)} tasks completed ({num_failed} failed)")

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
        databases=dataset.databases,
        subsample_size=dataset.subsample_size,
        dataset_extra_kwargs=dataset.dataset_extra_kwargs,
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


def parse_agent_config(agent_cls: type[NL2QAgent], args: argparse.Namespace) -> AgentConfig:
    kwargs: dict[str, Any] = {
        "schema_formatter": args.schema_formatter,
    }
    if args.llm is not None:
        kwargs["llm"] = args.llm
    if agent_cls.name == "sql_agent":
        if args.do_schema_linking is not None:
            kwargs["do_schema_linking"] = args.do_schema_linking
        if args.do_postprocessing is not None:
            kwargs["do_postprocessing"] = args.do_postprocessing
        if args.num_few_shot_examples is not None:
            kwargs["num_few_shot_examples"] = args.num_few_shot_examples
        if args.question_embedder_embedding_llm is not None:
            kwargs["question_embedder_embedding_llm"] = args.question_embedder_embedding_llm
    if agent_cls.name in ("tabulaflow_agent", "dbt_agent"):
        if args.db_summarizer_llm is not None:
            kwargs["db_summarizer_llm"] = args.db_summarizer_llm
    if agent_cls.name == "dbt_agent":
        if args.use_bash_tool is not None:
            kwargs["use_bash_tool"] = args.use_bash_tool
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature
    if args.max_steps is not None:
        kwargs["max_steps"] = args.max_steps
    if args.use_column_descriptions is not None:
        kwargs["use_column_descriptions"] = args.use_column_descriptions
    if args.no_query_for_intended_only:
        kwargs["query_for_intended_only"] = False
    if args.use_gold_phrases:
        kwargs["use_gold_phrases"] = True
    if args.use_gold_ambiguity_points:
        kwargs["use_gold_ambiguity_points"] = True
    if args.user_patience is not None:
        kwargs["user_patience"] = args.user_patience
    if args.reasoning_effort is not None:
        kwargs["reasoning_effort"] = args.reasoning_effort
    if args.service_tier is not None:
        kwargs["service_tier"] = args.service_tier
    return agent_cls.config_cls(**kwargs)


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="sql_agent")
    parser.add_argument("-s", "--schema_formatter", default=None)
    parser.add_argument("--llm", default=None)
    parser.add_argument("--temperature", default=None, type=float)
    parser.add_argument("--max_steps", default=None, type=int)
    parser.add_argument("--reasoning_effort", default=None)
    parser.add_argument("--service_tier", default=None)
    parser.add_argument("--use_column_descriptions", type=bool_flag, nargs="?", const=True, default=None)
    # sql agent
    parser.add_argument("--do_schema_linking", type=bool_flag, nargs="?", const=True, default=None)
    parser.add_argument("--do_postprocessing", type=bool_flag, nargs="?", const=True, default=None)
    parser.add_argument("--num_few_shot_examples", default=None, type=int)
    parser.add_argument("--few_shot_dataset", default="bird-sql")
    parser.add_argument("--few_shot_split", default="train")

    # tabulaflow/dbt agent
    parser.add_argument("--db_summarizer_llm", default=None)
    parser.add_argument("--use_bash_tool", type=bool_flag, nargs="?", const=True, default=None)

    # question embedder
    parser.add_argument("--question_embedder_embedding_llm", default=None)

    # ambig agents
    parser.add_argument("--no_query_for_intended_only", action="store_true")
    parser.add_argument("--use_gold_phrases", action="store_true")
    parser.add_argument("--use_gold_ambiguity_points", action="store_true")
    parser.add_argument("--user_patience", default=None)

    # dataset
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default=None)
    parser.add_argument("--databases", default=None, nargs="+")
    parser.add_argument("--qids", default=None, nargs="+")
    parser.add_argument("--subsample_size", default=None, type=int)
    parser.add_argument("--difficulty", default=None, choices=["simple", "moderate", "challenging"])
    parser.add_argument("--include_taxonomy", action="store_true")

    parser.add_argument("--batch_size", default=None, type=int)
    parser.add_argument("--sleep_between_batches", default=0.0, type=float)
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()
    if args.split is None:
        args.split = "test" if args.dataset in {"spider2-snow", "spider2-dbt", "arcs", "cypherbench"} else "dev"
    if args.schema_formatter is None:
        if args.dataset == "arcs":
            args.schema_formatter = "sql_basic"
        elif args.dataset == "cypherbench":
            args.schema_formatter = "cypher"
        else:
            args.schema_formatter = "sql_ddl"
    if args.num_few_shot_examples is None and args.dataset in {
        "bird-sql",
        "spider2-snow",
        "spider2-dbt",
        "cypherbench",
    }:
        args.num_few_shot_examples = 5 if args.dataset == "bird-sql" and args.agent == "sql_agent" else 0

    if args.debug:
        if args.batch_size is None:
            args.batch_size = 2
        args.overwrite = True
        if args.dataset == "spider2-snow" and not args.qids:
            args.databases = ["AIRLINES"]
        elif args.dataset == "spider2-dbt" and not args.qids:
            args.databases = ["zuora001"]
        elif args.dataset == "cypherbench" and not args.qids:
            args.databases = ["nba"]
    if args.batch_size is None:
        args.batch_size = 8
    print(args)
    print()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    configure_research_observability()

    if os.path.exists(args.result_dir):
        if not args.overwrite:
            print(f"{args.result_dir} already exists. Use --overwrite to overwrite the directory.")
            return
        else:
            shutil.rmtree(args.result_dir)
    os.makedirs(args.result_dir)

    t0 = time.time()
    kwargs = {}
    if args.include_taxonomy:
        kwargs["include_taxonomy"] = True
    dataset_loader = dataset_registry.get_class(args.dataset)(**kwargs)

    kwargs = {}
    if args.difficulty is not None:
        kwargs["difficulty"] = args.difficulty
    dataset = await dataset_loader.get_split_async(
        args.split, databases=args.databases, subsample_size=args.subsample_size, **kwargs
    )
    if args.qids is not None:
        dataset.tasks = [task for task in dataset.tasks if task.qid in args.qids]
    elif args.debug:
        dataset.tasks = dataset.tasks[:5]
        dataset.db_connectors = {
            key: connector
            for key, connector in dataset.db_connectors.items()
            if any(key == task.db for task in dataset.tasks)
        }

    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases from {args.dataset} ({args.split}) in {time.time() - t0:.2f} seconds."
    )

    if len(dataset.tasks) == 0:
        raise ValueError(f"No tasks loaded from {args.dataset} ({args.split})")

    few_shot_dataset = None
    if args.num_few_shot_examples is not None and args.num_few_shot_examples > 0:
        t0 = time.time()
        few_shot_dataset_loader = dataset_registry.get_class(args.few_shot_dataset)()
        few_shot_dataset = await few_shot_dataset_loader.get_split_async(args.few_shot_split)
        print(
            f"Loaded {len(few_shot_dataset.tasks)} tasks and {len(few_shot_dataset.db_connectors)} databases from {args.few_shot_dataset} ({args.few_shot_split}) in {time.time() - t0:.2f} seconds."
        )

    agent_class = agent_registry.get_class(args.agent)
    agent_config = parse_agent_config(agent_class, args)
    print(f"Running agent {agent_class.name} with config:")
    print(agent_config.model_dump_json(indent=2))

    t0 = time.time()
    result = await run_agent_async(
        agent_cls=agent_class,
        agent_config=agent_config,
        dataset=dataset,
        few_shot_dataset=few_shot_dataset,
        batch_size=args.batch_size,
        result_dir=args.result_dir,
        sleep_between_batches=args.sleep_between_batches,
        verbose=True,
    )
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
