import argparse
import asyncio
import collections
import datetime
import logging
import os
import time
import traceback
from functools import reduce
from typing import Any

from tabulaflow import dataset_registry
import tabulaflow
from tabulaflow.research.agenthub.ensemblers.majority_ensembler import MajorityEnsembler, MajorityEnsemblerConfig
from tabulaflow.research.agenthub.ensemblers.llm_ensembler import LLMEnsembler, LLMEnsemblerConfig
from tabulaflow.research.agenthub.ensemblers.agent_ensembler import AgentEnsembler, AgentEnsemblerConfig
from tabulaflow.research.agenthub.ensemblers.dbt_llm_ensembler import DbtLLMEnsembler, DbtLLMEnsemblerConfig
from tabulaflow.research.metrics import SimpleInferenceMetricsAggregator
from tabulaflow.research.types import NL2QRunResult, NL2QDataset, NL2QTaskOutput
from tabulaflow.research.pipelines.utils import bool_flag
from tabulaflow.core.utils import tqdm_gather_with_exceptions

Ensembler = MajorityEnsembler | LLMEnsembler | AgentEnsembler | DbtLLMEnsembler

logger = logging.getLogger(__name__)


async def _ensemble_tasks_async(
    ensembler: Ensembler,
    results: list[NL2QRunResult],
    dataset: NL2QDataset,
    batch_size: int,
    verbose: bool = True,
) -> tuple[list[NL2QTaskOutput], int]:
    """Ensemble NL2Q tasks. Returns (outputs, num_failed)."""
    qid_to_outputs: dict[str, list[NL2QTaskOutput]] = collections.defaultdict(list)
    for result in results:
        for task_output in result.tasks:
            qid_to_outputs[task_output.qid].append(task_output)

    tasks = []
    task_output_groups: list[list[NL2QTaskOutput]] = []
    for task in dataset.tasks:
        outputs = qid_to_outputs.get(task.qid, [])
        if not outputs:
            raise ValueError(f"No outputs found for task {task.qid}")
        tasks.append(task)
        task_output_groups.append(outputs)

    ensembled_outputs: list[NL2QTaskOutput] = []
    num_failed = 0
    for i in range(0, len(tasks), batch_size):
        j = min(i + batch_size, len(tasks))
        batch_tasks = tasks[i:j]
        batch_groups = task_output_groups[i:j]

        batch_results = await tqdm_gather_with_exceptions(
            *[
                ensembler.ensemble_async(task, dataset.db_connectors[task.db], outputs)
                for task, outputs in zip(batch_tasks, batch_groups)
            ],
            return_exceptions=True,
            disable=not verbose,
        )

        for task, group, output in zip(batch_tasks, batch_groups, batch_results):
            if isinstance(output, Exception):
                tb_str = "".join(traceback.format_exception(type(output), output, output.__traceback__))
                logger.error(f"Error ensembling task {task.qid}: {tb_str}")
                ensembled_outputs.append(group[0])
                num_failed += 1
            elif isinstance(output, BaseException):
                raise output
            else:
                ensembled_outputs.append(output)

        if verbose:
            print(f"{j}/{len(tasks)} tasks ensembled ({num_failed} failed)")

    return ensembled_outputs, num_failed


async def ensemble_async(
    ensembler: Ensembler,
    results: list[NL2QRunResult],
    dataset: NL2QDataset,
    batch_size: int,
    verbose: bool = True,
) -> NL2QRunResult:
    """Ensemble multiple run results into a single result.

    Args:
        ensembler: The ensembler instance.
        results: List of run results to ensemble.
        dataset: The dataset (used for db connectors).
        batch_size: Number of tasks to process concurrently.
        verbose: Whether to print progress.

    Returns:
        A new NL2QRunResult with ensembled predictions.
    """
    start_time = datetime.datetime.now()

    ensembled_outputs, num_failed = await _ensemble_tasks_async(ensembler, results, dataset, batch_size, verbose)

    end_time = datetime.datetime.now()

    usages = [t.usage for t in ensembled_outputs if t.usage is not None]

    res = NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=results[0].dataset,
        split=results[0].split,
        databases=results[0].databases,
        subsample_size=results[0].subsample_size,
        dataset_extra_kwargs=results[0].dataset_extra_kwargs,
        agent=ensembler.name,
        agent_config=ensembler.config.model_dump(),
        total_usage=reduce(lambda x, y: x + y, usages) if usages else None,
        aggregated_inference_metrics={},
        tasks=ensembled_outputs,
    )
    for aggregator in [SimpleInferenceMetricsAggregator()]:
        res.aggregated_inference_metrics.update(aggregator.aggregate(res))
    return res


def _build_llm_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Extract common LLM-related kwargs from CLI args."""
    kwargs: dict[str, Any] = {"result_dirs": args.result_dirs}
    if args.llm is not None:
        kwargs["llm"] = args.llm
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature
    if args.reasoning_effort is not None:
        kwargs["reasoning_effort"] = args.reasoning_effort
    if args.deduplicate_results is not None:
        kwargs["deduplicate_results"] = args.deduplicate_results
    return kwargs


def parse_ensembler(args: argparse.Namespace) -> Ensembler:
    """Build an ensembler instance from parsed CLI arguments."""
    if args.ensembler == "llm_ensembler":
        return LLMEnsembler(LLMEnsemblerConfig(**_build_llm_kwargs(args)))
    elif args.ensembler == "agent_ensembler":
        kwargs = _build_llm_kwargs(args)
        if args.max_steps is not None:
            kwargs["max_steps"] = args.max_steps
        return AgentEnsembler(AgentEnsemblerConfig(**kwargs))
    elif args.ensembler == "dbt_llm_ensembler":
        return DbtLLMEnsembler(DbtLLMEnsemblerConfig(**_build_llm_kwargs(args)))
    else:
        return MajorityEnsembler(MajorityEnsemblerConfig(result_dirs=args.result_dirs))


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Ensemble multiple result directories.")
    parser.add_argument("result_dirs", nargs="+", help="Paths to result directories to ensemble.")
    parser.add_argument("--output_dir", required=True, help="Path to save ensembled result.")
    parser.add_argument(
        "--ensembler",
        choices=["majority_ensembler", "llm_ensembler", "agent_ensembler", "dbt_llm_ensembler"],
        default="majority_ensembler",
        help="Ensembler strategy.",
    )
    parser.add_argument("--llm", type=str, default=None, help="LLM model identifier (for llm/agent ensembler).")
    parser.add_argument("--temperature", type=float, default=None, help="Temperature for llm/agent ensembler.")
    parser.add_argument("--reasoning_effort", default=None, help="Reasoning effort for llm/agent ensembler.")
    parser.add_argument(
        "--deduplicate_results",
        type=bool_flag,
        nargs="?",
        const=True,
        default=True,
        help="Deduplicate candidates with identical results (llm/agent ensembler, default true).",
    )
    parser.add_argument("--max_steps", type=int, default=None, help="Maximum agent steps (agent ensembler only).")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    tabulaflow.configure()

    if os.path.exists(args.output_dir):
        if not args.overwrite:
            print(f"{args.output_dir} already exists. Use --overwrite to overwrite.")
            return
    os.makedirs(args.output_dir, exist_ok=True)

    # Load all results
    results: list[NL2QRunResult] = []
    for result_dir in args.result_dirs:
        path = os.path.join(result_dir, "result.json")
        print(f"Loading {path} ...")
        with open(path, "r") as f:
            results.append(NL2QRunResult.model_validate_json(f.read()))
    print(f"Loaded {len(results)} results.")

    # Validate that all results are from the same dataset/split
    datasets = set((r.dataset, r.split) for r in results)
    if len(datasets) > 1:
        raise ValueError(f"All results must be from the same dataset/split, got: {datasets}")

    # Load dataset for db connectors
    t0 = time.time()
    ref = results[0]
    dataset_loader = dataset_registry.get_class(ref.dataset)()
    dataset = await dataset_loader.get_split_async(
        ref.split, databases=ref.databases, subsample_size=ref.subsample_size
    )
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {ref.dataset} {ref.split} in {time.time() - t0:.2f} seconds."
    )

    ensembler = parse_ensembler(args)

    t0 = time.time()
    result = await ensemble_async(ensembler, results, dataset, args.batch_size)
    latency = time.time() - t0
    print(f"\nEnsembled {len(result.tasks)} tasks in {latency:.2f} seconds.")
    cost = "N/A" if result.total_usage is None else f"{result.total_usage.api_cost_usd:.6f}"
    print(f"Total cost USD: {cost}")

    result.to_directory(args.output_dir)
    print(f"Saved ensembled result to {args.output_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
