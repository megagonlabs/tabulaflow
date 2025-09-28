import argparse
import os
import shutil
import time
from typing import Type
import datetime
import asyncio
import logfire
import litellm
from tqdm import trange
from mintq import agent_registry, dataset_registry
from mintq.utils import aggregate_metrics
from mintq.agenthub import NL2QAgent, BaseAgentConfig, SQLAgentConfig
from mintq.agenthub.user_simulator import UserSimulator
from mintq.schema import NL2QDataset, NL2QRunResult, Usage


logfire.configure(service_name="otel", send_to_logfire="if-token-present", console=False)
logfire.instrument_pydantic_ai()


async def run_agent_async(
    agent_cls: Type[NL2QAgent], agent_config: BaseAgentConfig, dataset: NL2QDataset, batch_size: int
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

        agents: list[NL2QAgent] = await asyncio.gather(*[agent_cls.from_config_async(agent_config) for _ in batch])
        task_outputs += await asyncio.gather(
            *[
                agent.predict_async(task, dataset.db_connectors[task.db], **kwargs)  # type: ignore
                for agent, task, kwargs in zip(agents, batch, batch_kwargs)
            ]
        )

        if i == 0:
            if getattr(task_outputs[0], "trajectory", None):
                print(task_outputs[0].trajectory.to_readable())  # type: ignore

    aggregated_metrics = aggregate_metrics(
        [task.inference_metrics for task in task_outputs], ops=["avg", "sum", "max"], decimals=4
    )

    end_time = datetime.datetime.now()
    return NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=dataset.name,
        split=dataset.split,
        subsample_size=dataset.subsample_size,
        databases=dataset.databases,
        agent=agent_cls.name,
        agent_args=agent_config.to_dict(),
        aggregated_inference_metrics=aggregated_metrics,
        tasks=task_outputs,
    )


def parse_agent_config(agent_cls: Type[NL2QAgent], args: argparse.Namespace) -> BaseAgentConfig:
    if agent_cls.name == "sql_agent":
        return SQLAgentConfig(
            llm=args.llm,
            schema_formatter=args.schema_formatter,
            temperature=args.temperature,
            num_candidates=args.num_majority_voting_candidates,
        )
    else:
        raise ValueError(f"Unsupported agent: {agent_cls.name}")


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="sql_agent")
    parser.add_argument("-s", "--schema_formatter", default="sql_default")
    parser.add_argument("--llm", default="openai:gpt-4o")
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

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split, databases=args.databases)
    if args.debug:
        dataset.tasks = dataset.tasks[:5]
    print(
        f"Loaded {len(dataset.tasks)} samples and {len(dataset.db_connectors)} databases from {args.dataset} {args.split} set in {time.time() - t0:.2f} seconds."
    )

    agent_class = agent_registry.get_class(args.agent)
    config = parse_agent_config(agent_class, args)
    result = await run_agent_async(agent_class, config, dataset, args.batch_size)
    result.to_directory(args.result_dir)
    print(f"Saved result to {args.result_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
