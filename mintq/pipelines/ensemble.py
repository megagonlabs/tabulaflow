import argparse
import asyncio
import collections
import datetime
import logging
import os
import time
import traceback

from tqdm.asyncio import tqdm_asyncio
from mintq import dataset_registry
from mintq.agenthub.ensemblers.majority_ensembler import MajorityEnsembler, MajorityEnsemblerConfig
from mintq.config import mintq_config
from mintq.schema import NL2QRunResult, NL2QDataset, SimpleNL2QTask, SimpleNL2QTaskOutput

logger = logging.getLogger(__name__)


async def ensemble_async(
    ensembler: MajorityEnsembler,
    results: list[NL2QRunResult],
    dataset: NL2QDataset,
    batch_size: int,
    verbose: bool = True,
) -> NL2QRunResult:
    """Ensemble multiple run results into a single result via majority voting.

    Args:
        ensembler: The ensembler instance.
        results: List of run results to ensemble.
        dataset: The dataset (used for db connectors).
        batch_size: Number of tasks to process concurrently.
        verbose: Whether to print progress.

    Returns:
        A new NL2QRunResult with ensembled predictions.
    """
    # Build a mapping from qid to list of task outputs across all results
    qid_to_outputs: dict[str, list[SimpleNL2QTaskOutput]] = collections.defaultdict(list)
    for result in results:
        for task_output in result.tasks:
            assert isinstance(task_output, SimpleNL2QTaskOutput), (
                f"Ensemble only supports SimpleNL2QTaskOutput, got {type(task_output)}"
            )
            qid_to_outputs[task_output.qid].append(task_output)

    # Use the first result's task order as the canonical order
    tasks: list[SimpleNL2QTask] = []
    task_output_groups: list[list[SimpleNL2QTaskOutput]] = []
    for task_output in results[0].tasks:
        outputs = qid_to_outputs.get(task_output.qid, [])
        if not outputs:
            continue
        task = SimpleNL2QTask(**{k: v for k, v in task_output.model_dump().items() if k in SimpleNL2QTask.model_fields})
        tasks.append(task)
        task_output_groups.append(outputs)

    # Run ensemble in batches
    start_time = datetime.datetime.now()
    ensembled_outputs: list[SimpleNL2QTaskOutput] = []
    num_failed = 0
    for i in range(0, len(tasks), batch_size):
        j = min(i + batch_size, len(tasks))
        batch_tasks = tasks[i:j]
        batch_groups = task_output_groups[i:j]

        batch_results = await tqdm_asyncio.gather(
            *[
                ensembler.ensemble_async(task, dataset.db_connectors[task.db], outputs)
                for task, outputs in zip(batch_tasks, batch_groups)
            ],
            return_exceptions=True,
            disable=not verbose,
        )

        for task, output in zip(batch_tasks, batch_results):
            if isinstance(output, Exception):
                tb_str = "".join(traceback.format_exception(type(output), output, output.__traceback__))
                logger.error(f"Error ensembling task {task.qid}: {tb_str}")
                ensembled_outputs.append(SimpleNL2QTaskOutput(**task.model_dump(), pred_query=None))
                num_failed += 1
            elif isinstance(output, BaseException):
                raise output
            else:
                ensembled_outputs.append(output)

        if verbose:
            print(f"{j}/{len(tasks)} tasks ensembled ({num_failed} failed)")

    end_time = datetime.datetime.now()

    source_dirs = [r.agent for r in results]
    return NL2QRunResult(
        start_time=start_time,
        end_time=end_time,
        dataset=results[0].dataset,
        split=results[0].split,
        databases=results[0].databases,
        subsample_size=results[0].subsample_size,
        dataset_extra_kwargs=results[0].dataset_extra_kwargs,
        agent="majority_ensembler",
        agent_config={"sources": source_dirs, "num_sources": len(results)},
        tasks=ensembled_outputs,
    )


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Ensemble multiple result directories via majority voting.")
    parser.add_argument("result_dirs", nargs="+", help="Paths to result directories to ensemble.")
    parser.add_argument("--output_dir", required=True, help="Path to save ensembled result.")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    mintq_config.setup_logging()

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

    ensembler = MajorityEnsembler(MajorityEnsemblerConfig())

    t0 = time.time()
    result = await ensemble_async(ensembler, results, dataset, args.batch_size)
    print(f"\nEnsembled {len(result.tasks)} tasks in {time.time() - t0:.2f} seconds.")

    result.to_directory(args.output_dir)
    print(f"Saved ensembled result to {args.output_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
