import statistics
from typing import Any, Literal, cast

from tabulaflow.research.types import AmbigNL2QTask, NL2QRunResult, NumericOrNull


def _enforce_same_schema(metrics: list[dict[str, Any]]) -> None:
    if not all(metric.keys() == metrics[0].keys() for metric in metrics):
        raise ValueError("All metrics to aggregate must have the same schema.")
    for key in metrics[0]:
        if isinstance(metrics[0][key], dict):
            _enforce_same_schema([metric[key] for metric in metrics])


def aggregate_metrics(
    metrics: list[NumericOrNull] | list[dict[str, Any]],
    ops: list[Literal["avg", "sum", "max", "min"]] = ["avg", "sum", "max", "min"],
    decimals: int = 4,
) -> dict[str, Any]:
    """Aggregate scalar or consistently nested metric values."""
    if not metrics:
        return {op: None for op in ops}
    if isinstance(metrics[0], dict):
        _enforce_same_schema(metrics)  # type: ignore[arg-type]
        return {key: aggregate_metrics([metric[key] for metric in metrics], ops, decimals) for key in metrics[0]}  # type: ignore[index]
    values = [metric for metric in cast(list[NumericOrNull], metrics) if metric is not None]
    if not values:
        return {op: None for op in ops}
    result: dict[str, Any] = {}
    for op in ops:
        if op == "avg":
            value = statistics.mean(values)
        elif op == "sum":
            value = sum(values)
        elif op == "max":
            value = max(values)
        else:
            value = min(values)
        result[op] = round(value, decimals)
    return result


class RealScoreAggregator:
    """Aggregator that divides by total dataset size, treating missing tasks as 0.

    Unlike SimpleAverageAggregator which divides by the number of evaluated
    tasks, this divides by the known dataset size so that unevaluated/missing
    predictions are implicitly counted as failures.
    """

    DATASET_CONFIGS: dict[tuple[str, str], tuple[int, str]] = {
        ("bird-sql", "dev"): (1534, "bird_sql_ex"),
        ("bird-sql", "dev_20251106"): (1534, "bird_sql_ex"),
        ("bird-sql", "train"): (9428, "bird_sql_ex"),
        ("spider2-snow", "test"): (547, "spider2_ex"),
        ("spider2-lite", "test"): (547, "spider2_ex"),
        ("spider2-dbt", "test"): (68, "spider2_duckdb_match"),
        ("beaver", "test"): (209, "simple_ex"),
        ("arcs", "test"): (331, "simple_ex"),
        ("arcs", "test_unsampled"): (101, "simple_ex"),
        ("ambrosia-s", "test"): (1149, "simple_ex"),
        ("ambrosia-s", "few_shot_examples"): (128, "simple_ex"),
    }

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        config = self.DATASET_CONFIGS.get((result.dataset, result.split))
        if config is None:
            return {}
        total_tasks, metric_key = config
        if all(metric_key not in task.eval_metrics for task in result.tasks):
            return {}
        values = [task.eval_metrics[metric_key] for task in result.tasks]
        total = sum(v for v in values if v is not None)
        return {f"{metric_key}_real": round(total / total_tasks, 4)}


class SimpleInferenceMetricsAggregator:
    def __init__(self, ops: list[Literal["avg", "sum", "max", "min"]] = ["avg", "sum", "max"]):
        self.ops = ops

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        return aggregate_metrics(
            [task.inference_metrics for task in result.tasks if task.inference_metrics], ops=self.ops, decimals=4
        )


class SimpleAverageAggregator:
    def __init__(self, ops: list[Literal["avg", "sum", "max", "min"]] = ["avg"]):
        self.ops = ops

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        return aggregate_metrics([task.eval_metrics for task in result.tasks], ops=self.ops, decimals=4)


class ByDBAggregator:
    def __init__(
        self,
        ops: list[Literal["avg", "sum", "max", "min"]] = ["avg"],
        metric_keys: list[str] = ["simple_ex", "perfect_linked_schema_r"],
        max_dbs: int = 200,
    ):
        self.ops = ops
        self.metric_keys = metric_keys
        self.max_dbs = max_dbs

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        databases = result.databases or list(dict.fromkeys([task.db for task in result.tasks]))

        if len(databases) > self.max_dbs:
            return {}

        res = {}
        for metric_key in self.metric_keys:
            if metric_key not in result.tasks[0].eval_metrics:
                continue

            metrics = {}
            for db in databases:
                metrics[db] = aggregate_metrics(
                    [task.eval_metrics[metric_key] for task in result.tasks if task.db == db], ops=self.ops, decimals=4
                )
            res[f"{metric_key}_by_db"] = metrics
        return res


class ByAmbigPointNumAggregator:
    def __init__(
        self, ops: list[Literal["avg", "sum", "max", "min"]] = ["avg"], metric_keys: list[str] = ["simple_ex"]
    ):
        self.ops = ops
        self.metric_keys = metric_keys

    def _num_aps(self, task: AmbigNL2QTask, finite_only: bool = False) -> int:
        return len([ap for ap in task.gold_ambiguity_points if not finite_only or ap.type == "finite"])

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        ambig_tasks = [task for task in result.tasks if task.task_type == "ambig"]
        if not ambig_tasks:
            return {}

        res = {}
        for metric_key in self.metric_keys:
            metrics = {}
            metrics["1AP"] = aggregate_metrics(
                [task.eval_metrics[metric_key] for task in ambig_tasks if self._num_aps(task) == 1],
                ops=self.ops,
                decimals=4,
            )
            metrics["2AP"] = aggregate_metrics(
                [task.eval_metrics[metric_key] for task in ambig_tasks if self._num_aps(task) == 2],
                ops=self.ops,
                decimals=4,
            )
            metrics["3+AP"] = aggregate_metrics(
                [task.eval_metrics[metric_key] for task in ambig_tasks if self._num_aps(task) >= 3],
                ops=self.ops,
                decimals=4,
            )
            res[f"{metric_key}_by_ambig_point_num"] = metrics
        return res


class ByAmbrosiaTaxonomyTypeAggregator:
    def __init__(
        self, ops: list[Literal["avg", "sum", "max", "min"]] = ["avg"], metric_keys: list[str] = ["simple_ex"]
    ):
        self.ops = ops
        self.metric_keys = metric_keys

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        if result.dataset != "ambrosia-s":
            return {}

        all_types = ["scope", "attachment", "vague"]
        res = {}
        for metric_key in self.metric_keys:
            metrics = {}
            for t in all_types:
                metrics[t] = aggregate_metrics(
                    [
                        task.eval_metrics[metric_key]
                        for task in result.tasks
                        if task.extra_info["ambrosia"]["ambig_type"] == t
                    ],
                    ops=self.ops,
                    decimals=4,
                )
            res[f"{metric_key}_by_taxonomy_type"] = metrics
        return res


class ByBirdSQLDifficultyAggregator:
    def __init__(
        self,
        ops: list[Literal["avg", "sum", "max", "min"]] = ["avg"],
        metric_keys: list[str] = ["bird_sql_ex", "simple_ex", "perfect_linked_schema_r"],
    ):
        self.ops = ops
        self.metric_keys = metric_keys

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        if result.dataset != "bird-sql":
            return {}

        all_levels = ["simple", "moderate", "challenging"]
        res = {}
        for metric_key in self.metric_keys:
            metrics = {}
            for level in all_levels:
                metrics[level] = aggregate_metrics(
                    [
                        task.eval_metrics[metric_key]
                        for task in result.tasks
                        if task.extra_info["bird_sql"]["difficulty"] == level
                    ],
                    ops=self.ops,
                    decimals=4,
                )
            res[f"{metric_key}_by_difficulty"] = metrics
        return res
