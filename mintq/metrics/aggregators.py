from typing import Any, Literal
from mintq.schema import AmbigNL2QTask, NL2QRunResult
from mintq.utils import aggregate_metrics


class SimpleInferenceMetricsAggregator:
    def __init__(self, ops: list[Literal["avg", "sum", "max", "min"]] = ["avg", "sum", "max"]):
        self.ops = ops

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        return aggregate_metrics([task.inference_metrics for task in result.tasks], ops=self.ops, decimals=4)


class SimpleAverageAggregator:
    def __init__(self, ops: list[Literal["avg", "sum", "max", "min"]] = ["avg"]):
        self.ops = ops

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]:
        return aggregate_metrics([task.eval_metrics for task in result.tasks], ops=self.ops, decimals=4)


class ByDBAggregator:
    def __init__(
        self,
        ops: list[Literal["avg", "sum", "max", "min"]] = ["avg"],
        metric_keys: list[str] = ["simple_ex"],
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
        if result.dataset != "ambrosia_s":
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
