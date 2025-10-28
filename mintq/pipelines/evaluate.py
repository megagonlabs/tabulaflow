import argparse
import asyncio
import os
from tqdm import trange
from mintq import metric_registry
from mintq.schema import NL2QTaskOutput, NL2QRunResult
from mintq.utils import aggregate_metrics
from mintq.metrics import NL2QMetric


async def compute_metrics_async(task: NL2QTaskOutput, metrics: list[NL2QMetric]) -> NL2QTaskOutput:
    results = await asyncio.gather(*[m.compute_async(task) for m in metrics])  # type: ignore
    task.eval_metrics = {}
    for m, r in zip(metrics, results):
        if isinstance(r, dict):
            task.eval_metrics.update(r)
        else:
            task.eval_metrics[m.name] = r
    return task


async def evaluate_async(result: NL2QRunResult, metrics: list[NL2QMetric], batch_size: int) -> NL2QRunResult:
    for i in trange(0, len(result.tasks), batch_size):
        await asyncio.gather(*[compute_metrics_async(task, metrics) for task in result.tasks[i : i + batch_size]])
    result.aggregated_eval_metrics = aggregate_metrics(
        [task.eval_metrics for task in result.tasks], ops=["avg"], decimals=4
    )
    return result


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=[
            "simple_ex",
            "spider2_ex",
            "bird_sql_ex",
            "bird_sql_ex_soft",
            "executable",
            "gold_executable",
            "gold_result_not_empty",
            "ambig_point_stats",
            "pred_success",
        ],
    )
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    unique_output_types = list(dict.fromkeys([task.output_type for task in result.tasks]))
    metrics = []
    for m in args.metrics:
        metric_cls = metric_registry.get_class(m)
        if any(output_type not in metric_cls.compatible_output_types for output_type in unique_output_types):
            print(f"Metric {m} is not compatible with at least one output type in {unique_output_types}, skipping...")
            continue
        metrics.append(metric_cls())
    result = await evaluate_async(result, metrics, args.batch_size)

    result.to_directory(args.result_dir, eval_metrics_in_summary=args.metrics)
    print(f"Saved evaluated result to {args.result_dir}")

    print()
    print("Aggregated metrics:")
    for key in result.aggregated_eval_metrics:
        print(f"- {key}: {result.aggregated_eval_metrics[key]['avg']:.4f}")

    if args.debug:
        print()
        print("=== DEBUG MODE === ")
        for task in result.tasks:
            print(f"{task.qid}: {task.eval_metrics['simple_ex']:.4f}")


if __name__ == "__main__":
    asyncio.run(main_async())
