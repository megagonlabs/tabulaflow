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

from tabulaflow.research.benchmarks.registry import dataset_registry
from tabulaflow.research.observability import configure_research_observability
from tabulaflow.research.agents.ensemblers.majority import MajorityEnsembler, MajorityEnsemblerConfig
from tabulaflow.research.agents.ensemblers.llm import LLMEnsembler, LLMEnsemblerConfig
from tabulaflow.research.agents.ensemblers.agent import AgentEnsembler, AgentEnsemblerConfig
from tabulaflow.research.agents.ensemblers.dbt import DbtLLMEnsembler, DbtLLMEnsemblerConfig
from tabulaflow.research.metrics import SimpleInferenceMetricsAggregator
from tabulaflow.research.types import NL2QRunResult, NL2QDataset, NL2QTaskOutput
from tabulaflow.research.pipelines.utils import bool_flag
from tabulaflow.research.pipelines.utils import tqdm_gather_with_exceptions

Ensembler = MajorityEnsembler | LLMEnsembler | AgentEnsembler | DbtLLMEnsembler

logger = logging.getLogger(__name__)


def _validate_results(results: list[NL2QRunResult], output_type: str | None = None) -> NL2QRunResult:
    """Validate ensemble inputs and return the reference run."""
    if not results:
        raise ValueError("At least one result is required")

    reference = results[0]
    reference_qids = {task.qid for task in reference.tasks}
    for result in results:
        if (result.dataset, result.split) != (reference.dataset, reference.split):
            raise ValueError("All results must use the same dataset and split")
        qids = [task.qid for task in result.tasks]
        if len(qids) != len(set(qids)):
            raise ValueError(f"Result for agent {result.agent!r} contains duplicate QIDs")
        if set(qids) != reference_qids:
            raise ValueError("All results must contain the same QIDs")
        if output_type is not None and any(task.output_type != output_type for task in result.tasks):
            raise ValueError(f"Ensembler requires {output_type!r} outputs")
    return reference


async def _ensemble_tasks_async(
    ensembler: Ensembler,
    results: list[NL2QRunResult],
    dataset: NL2QDataset,
    batch_size: int,
    verbose: bool = True,
) -> tuple[list[NL2QTaskOutput], int]:
    """Ensemble every task, falling back to the first candidate on failure."""
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
    fallback_count = 0
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
                logger.error(
                    "Error ensembling task %s:\n%s",
                    task.qid,
                    "".join(traceback.format_exception(type(output), output, output.__traceback__)),
                )
                fallback = group[0].model_copy(deep=True)
                fallback.usage = None
                fallback.trajectory = None
                fallback.inference_metrics = {}
                fallback.eval_metrics = {}
                if hasattr(fallback, "user_simulator_usage"):
                    fallback.user_simulator_usage = None
                ensembled_outputs.append(fallback)
                fallback_count += 1
            elif isinstance(output, BaseException):
                raise output
            else:
                ensembled_outputs.append(output)

        if verbose:
            print(f"{j}/{len(tasks)} tasks ensembled ({fallback_count} fallbacks)")

    return ensembled_outputs, fallback_count


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
        A new run result with ensembled predictions. Task-level failures fall
        back to the first candidate, clear its source-run metadata, and
        increment ``fallback_count`` in the aggregate inference metrics.
    """
    output_type = "dbt" if ensembler.name == "dbt_llm" else "simple"
    reference = _validate_results(results, output_type)
    if {task.qid for task in dataset.tasks} != {task.qid for task in reference.tasks}:
        raise ValueError("Dataset tasks must match the result QIDs")
    start_time = datetime.datetime.now()

    ensembled_outputs, fallback_count = await _ensemble_tasks_async(ensembler, results, dataset, batch_size, verbose)

    end_time = datetime.datetime.now()

    usages = [t.usage for t in ensembled_outputs if t.usage is not None]

    res = NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=reference.dataset,
        split=reference.split,
        databases=reference.databases,
        subsample_size=reference.subsample_size,
        dataset_extra_kwargs=reference.dataset_extra_kwargs,
        agent=ensembler.name,
        agent_config=ensembler.config.model_dump(),
        total_usage=reduce(lambda x, y: x + y, usages) if usages else None,
        aggregated_inference_metrics={},
        tasks=ensembled_outputs,
    )
    for aggregator in [SimpleInferenceMetricsAggregator()]:
        res.aggregated_inference_metrics.update(aggregator.aggregate(res))
    res.aggregated_inference_metrics["fallback_count"] = fallback_count
    return res


def _build_llm_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Extract common LLM-related kwargs from CLI args."""
    kwargs: dict[str, Any] = {"result_dirs": args.result_dirs}
    if args.llm is not None:
        kwargs["llm"] = args.llm
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature
    if args.reasoning is not None:
        kwargs["reasoning"] = args.reasoning
    if args.service_tier is not None:
        kwargs["service_tier"] = args.service_tier
    if args.deduplicate_results is not None:
        kwargs["deduplicate_results"] = args.deduplicate_results
    return kwargs


def parse_ensembler(args: argparse.Namespace) -> Ensembler:
    """Build an ensembler instance from parsed CLI arguments."""
    if args.ensembler == "llm":
        return LLMEnsembler(LLMEnsemblerConfig(**_build_llm_kwargs(args)))
    elif args.ensembler == "agent":
        kwargs = _build_llm_kwargs(args)
        if args.max_steps is not None:
            kwargs["max_steps"] = args.max_steps
        return AgentEnsembler(AgentEnsemblerConfig(**kwargs))
    elif args.ensembler == "dbt_llm":
        return DbtLLMEnsembler(DbtLLMEnsemblerConfig(**_build_llm_kwargs(args)))
    else:
        return MajorityEnsembler(MajorityEnsemblerConfig(result_dirs=args.result_dirs))


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Ensemble multiple result directories.")
    parser.add_argument("result_dirs", nargs="+", help="Paths to result directories to ensemble.")
    parser.add_argument("--output-dir", required=True, help="Path to save ensembled result.")
    parser.add_argument(
        "--ensembler",
        choices=["majority", "llm", "agent", "dbt_llm"],
        default="majority",
        help="Ensembler strategy.",
    )
    parser.add_argument("--llm", type=str, default=None, help="LLM model identifier for model-based ensemblers.")
    parser.add_argument("--temperature", type=float, default=None, help="Temperature for model-based ensemblers.")
    parser.add_argument("--reasoning", default=None, help="Reasoning effort for model-based ensemblers.")
    parser.add_argument("--service-tier", default=None, help="Service tier for model-based ensemblers.")
    parser.add_argument(
        "--deduplicate-results",
        type=bool_flag,
        nargs="?",
        const=True,
        default=None,
        help="Deduplicate candidates with identical results (LLM ensemblers, default true).",
    )
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum agent steps (agent ensembler only).")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--log-level", type=str.upper, choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="WARNING")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    if args.ensembler == "majority" and any(
        value is not None
        for value in (
            args.llm,
            args.temperature,
            args.reasoning,
            args.service_tier,
            args.deduplicate_results,
            args.max_steps,
        )
    ):
        parser.error("model options are not supported by the majority ensembler")
    if args.max_steps is not None and args.ensembler != "agent":
        parser.error("--max-steps requires --ensembler agent")
    print(args)
    print()

    configure_research_observability()

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

    ensembler = parse_ensembler(args)

    # Load dataset for db connectors
    t0 = time.time()
    output_type = "dbt" if ensembler.name == "dbt_llm" else "simple"
    ref = _validate_results(results, output_type)
    dataset_loader = dataset_registry.get_class(ref.dataset)()
    dataset = await dataset_loader.get_split_async(
        ref.split,
        databases=ref.databases,
        subsample_size=ref.subsample_size,
        qids=[task.qid for task in ref.tasks],
    )
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {ref.dataset} {ref.split} in {time.time() - t0:.2f} seconds."
    )

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
