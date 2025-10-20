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
from mintq.utils import aggregate_metrics
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
    verbose: bool = False,
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
            elif isinstance(output, BaseException):
                raise output
            else:
                task_outputs.append(output)

        if i == 0 and verbose:
            trajectory = getattr(task_outputs[0], "trajectory", None)
            if trajectory:
                for tr in trajectory if isinstance(trajectory, list) else [trajectory]:
                    print(tr.to_readable())

    end_time = datetime.datetime.now()

    usages = [t.usage for t in task_outputs if t.usage is not None]
    user_simulator_usages = [
        t.user_simulator_usage for t in task_outputs if t.task_type == "ambig" and t.user_simulator_usage
    ]

    return NL2QRunResult(
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
        aggregated_inference_metrics=aggregate_metrics(
            [task.inference_metrics for task in task_outputs if task.inference_metrics],
            ops=["avg", "sum", "max"],
            decimals=4,
        ),
        tasks=task_outputs,
    )


def parse_agent_config(agent_cls: type[NL2QAgent], args: argparse.Namespace) -> BaseAgentConfig:
    kwargs = {
        "llm": args.llm,
        "schema_formatter": args.schema_formatter,
        "temperature": args.temperature,
    }
    if agent_cls.name == "simple_zero_shot":
        kwargs["num_candidates"] = args.num_majority_voting_candidates
    return agent_cls.config_cls(**kwargs)


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="sql_agent")
    parser.add_argument("-s", "--schema_formatter", default="sql_default")
    parser.add_argument("--llm", default="openai-responses:gpt-4.1-mini")
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("-n", "--num_majority_voting_candidates", default=1, type=int)
    parser.add_argument("--local_llm_config", default="local_llm_config.json")

    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--databases", default=None, nargs="+")

    parser.add_argument("--batch_size", default=8, type=int)
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug_litellm", action="store_true")
    parser.add_argument("--log_level", default="INFO", type=str)
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

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    if args.debug:
        if args.dataset == "arcs":
            # dataset.tasks = dataset.tasks[10:13]
            dataset.tasks = [
                task
                for task in dataset.tasks
                if task.qid
                in [
                    "001",
                ]
            ]
        else:
            dataset.tasks = dataset.tasks[:5]
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    agent_class = agent_registry.get_class(args.agent)
    config = parse_agent_config(agent_class, args)
    result = await run_agent_async(agent_class, config, dataset, args.batch_size, verbose=True)
    result.to_directory(args.result_dir)
    print(f"Saved result to {args.result_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
