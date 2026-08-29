import argparse
import os
import shutil
import time
from functools import reduce
from typing import Any, cast
import datetime
import asyncio
import logging
import traceback
from pydantic import BaseModel
from tabulaflow.research.agents.registry import agent_registry
from tabulaflow.research.benchmarks.registry import dataset_registry
from tabulaflow.research.metrics import MetricAggregatorProtocol, SimpleInferenceMetricsAggregator
from tabulaflow.research.pipelines.utils import pprint_dict, tqdm_gather_with_exceptions
from tabulaflow.research.observability import configure_research_observability
from tabulaflow.research.pipelines.utils import bool_flag
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


def get_empty_output(agent_cls: type[Any], task: NL2QTask) -> NL2QTaskOutput:
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
    agent_cls: type[Any],
    agent_config: BaseModel,
    dataset: NL2QDataset,
    batch_size: int,
    few_shot_dataset: NL2QDataset | None = None,
    output_dir: str = "output/test/",
    metric_aggregators: list[MetricAggregatorProtocol] | None = None,
    verbose: bool = True,
) -> NL2QRunResult:
    if metric_aggregators is None:
        metric_aggregators = [SimpleInferenceMetricsAggregator()]
    if hasattr(agent_config, "llm") and Usage.create(agent_config.llm, 1, 1000000, 1000000).api_cost_usd == 0:
        logger.warning("API cost for %s is 0.0. Cost calculation might not be supported.", agent_config.llm)

    if dataset.name == "spider2-dbt":
        await prepare_working_env_async(dataset, output_dir)

    start_time = datetime.datetime.now()
    task_outputs = []
    num_failed = 0
    for i in range(0, len(dataset.tasks), batch_size):
        j = min(i + batch_size, len(dataset.tasks))
        batch = dataset.tasks[i:j]

        agent_kwargs = {}
        if few_shot_dataset is not None:
            agent_kwargs["few_shot_dataset"] = few_shot_dataset
        agents: list[Any] = await asyncio.gather(
            *(agent_cls.from_config_async(agent_config, **agent_kwargs) for _ in batch)
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
                agent.predict_async(task, dataset.db_connectors[task.db], **kwargs)
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


def parse_agent_config(agent_cls: type[Any], args: argparse.Namespace) -> BaseModel:
    kwargs: dict[str, Any] = {
        "schema_formatter": args.schema_formatter,
    }
    if args.llm is not None:
        kwargs["llm"] = args.llm
    if agent_cls.name == "schema_linking":
        if args.do_schema_linking is not None:
            kwargs["do_schema_linking"] = args.do_schema_linking
        if args.do_postprocessing is not None:
            kwargs["do_postprocessing"] = args.do_postprocessing
        if args.num_few_shot_examples is not None:
            kwargs["num_few_shot_examples"] = args.num_few_shot_examples
        if args.question_embedder_embedding_llm is not None:
            kwargs["question_embedder_embedding_llm"] = args.question_embedder_embedding_llm
    if agent_cls.name in ("schema_discovery", "dbt_agent"):
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
    if args.query_for_intended_only is not None:
        kwargs["query_for_intended_only"] = args.query_for_intended_only
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
    return cast(BaseModel, agent_cls.config_cls(**kwargs))


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group("general")
    general.add_argument("--agent", default="schema_linking")
    general.add_argument("--batch-size", type=int, default=8)
    general.add_argument("--output-dir", default="output/test/")
    general.add_argument("--overwrite", action="store_true")
    general.add_argument(
        "--log-level", type=str.upper, choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="WARNING"
    )

    dataset_options = parser.add_argument_group("dataset selection")
    dataset_options.add_argument("--dataset", default="bird-sql")
    dataset_options.add_argument("--split", default=None)
    dataset_options.add_argument("--databases", nargs="+", default=None)
    dataset_options.add_argument("--qids", nargs="+", default=None)
    dataset_options.add_argument("--subsample-size", type=int, default=None)
    dataset_options.add_argument("--difficulty", choices=["simple", "moderate", "challenging"], default=None)
    dataset_options.add_argument("--include-taxonomy", action="store_true")

    model = parser.add_argument_group("model settings")
    model.add_argument("--llm", default=None)
    model.add_argument("--temperature", type=float, default=None)
    model.add_argument("--max-steps", type=int, default=None)
    model.add_argument("--reasoning-effort", default=None)
    model.add_argument("--service-tier", default=None)
    model.add_argument("--use-column-descriptions", type=bool_flag, nargs="?", const=True, default=None)
    model.add_argument("-s", "--schema-formatter", default=None)

    schema_linking = parser.add_argument_group("schema-linking agent")
    schema_linking.add_argument("--do-schema-linking", type=bool_flag, nargs="?", const=True, default=None)
    schema_linking.add_argument("--do-postprocessing", type=bool_flag, nargs="?", const=True, default=None)
    schema_linking.add_argument("--num-few-shot-examples", type=int, default=None)
    schema_linking.add_argument("--few-shot-dataset", default=None)
    schema_linking.add_argument("--few-shot-split", default=None)
    schema_linking.add_argument("--question-embedder-embedding-llm", default=None)

    tool_agents = parser.add_argument_group("schema-discovery and DBT agents")
    tool_agents.add_argument("--db-summarizer-llm", default=None)
    tool_agents.add_argument("--use-bash-tool", type=bool_flag, nargs="?", const=True, default=None)

    ambiguity = parser.add_argument_group("ambiguity agents")
    ambiguity.add_argument("--query-for-intended-only", type=bool_flag, nargs="?", const=True, default=None)
    ambiguity.add_argument("--use-gold-phrases", action="store_true")
    ambiguity.add_argument("--use-gold-ambiguity-points", action="store_true")
    ambiguity.add_argument("--user-patience", default=None)

    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    if args.difficulty is not None and args.dataset != "bird-sql":
        parser.error("--difficulty is only supported for bird-sql")
    if args.include_taxonomy and args.dataset not in {"arcs", "ambrosia-s"}:
        parser.error("--include-taxonomy is only supported for arcs and ambrosia-s")
    if args.agent != "schema_linking" and any(
        value is not None
        for value in (
            args.do_schema_linking,
            args.do_postprocessing,
            args.num_few_shot_examples,
            args.few_shot_dataset,
            args.few_shot_split,
            args.question_embedder_embedding_llm,
        )
    ):
        parser.error("schema-linking options require --agent schema_linking")
    if args.db_summarizer_llm is not None and args.agent not in {"schema_discovery", "dbt_agent"}:
        parser.error("--db-summarizer-llm requires --agent schema_discovery or dbt_agent")
    if args.use_bash_tool is not None and args.agent != "dbt_agent":
        parser.error("--use-bash-tool requires --agent dbt_agent")
    if args.query_for_intended_only is not None and args.agent not in {
        "ambig_flat_sql_agent",
        "ambig_structured_sql_agent",
    }:
        parser.error("--query-for-intended-only requires a flat or structured ambiguity agent")
    if (args.use_gold_phrases or args.use_gold_ambiguity_points) and args.agent != "ambig_structured_sql_agent":
        parser.error("gold ambiguity options require --agent ambig_structured_sql_agent")
    if args.user_patience is not None and args.agent != "ambig_simple_sql_agent":
        parser.error("--user-patience requires --agent ambig_simple_sql_agent")

    if args.agent == "schema_linking":
        args.few_shot_dataset = args.few_shot_dataset or "bird-sql"
        args.few_shot_split = args.few_shot_split or "train"

    loader_kwargs = {"include_taxonomy": True} if args.include_taxonomy else {}
    dataset_loader = dataset_registry.get_class(args.dataset)(**loader_kwargs)
    if args.split is None:
        args.split = dataset_loader.splits[0]
    if args.schema_formatter is None:
        if args.dataset == "arcs":
            args.schema_formatter = "sql_basic"
        elif args.dataset == "cypherbench":
            args.schema_formatter = "cypher"
        else:
            args.schema_formatter = "sql_ddl"
    if args.agent == "schema_linking" and args.num_few_shot_examples is None:
        args.num_few_shot_examples = 5 if args.dataset == "bird-sql" else 0

    print(args)
    print()

    configure_research_observability()

    if os.path.exists(args.output_dir):
        if not args.overwrite:
            print(f"{args.output_dir} already exists. Use --overwrite to overwrite the directory.")
            return
        else:
            shutil.rmtree(args.output_dir)
    os.makedirs(args.output_dir)

    t0 = time.time()
    kwargs = {}
    if args.difficulty is not None:
        kwargs["difficulty"] = args.difficulty
    dataset = await dataset_loader.get_split_async(
        args.split,
        databases=args.databases,
        subsample_size=args.subsample_size,
        qids=args.qids,
        **kwargs,
    )

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
        output_dir=args.output_dir,
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

    result.to_directory(args.output_dir)
    print()
    print(f"Saved result to {args.output_dir}")

    print()
    print("Aggregated inference metrics:")
    print(pprint_dict(result.aggregated_inference_metrics))


if __name__ == "__main__":
    asyncio.run(main_async())
