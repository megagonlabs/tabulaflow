from typing import Any
from itertools import combinations
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.schema import SimpleNL2QTaskOutput


class BirdSQLExSoft:
    name = "bird_sql_ex_soft"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def _compare(self, pred_executed: list[tuple[Any, ...]], gold_executed: list[tuple[Any, ...]]) -> float:
        if not gold_executed and not pred_executed:
            return 1.0
        elif not gold_executed or not pred_executed:
            return 0.0

        n_cols_gold = len(gold_executed[0])
        n_cols_pred = len(pred_executed[0])

        # Determine whether there exists a subset of columns in pred_executed that is equal to gold_executed
        if n_cols_gold > n_cols_pred:
            return 0.0

        # Convert results to sets of tuples for comparison
        gold_set = set(tuple(row) for row in gold_executed)

        # Try all possible column combinations of pred_executed that match gold_executed's width
        for col_indices in combinations(range(n_cols_pred), n_cols_gold):
            # Extract the subset of columns from pred_executed
            pred_subset = set(tuple(row[i] for i in col_indices) for row in pred_executed)

            # If we found a matching subset, return 1.0
            if pred_subset == gold_set:
                return 1.0
        return 0.0

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncSQLDBConnector) -> float:
        if task.pred_exec_result is None:
            return 0.0

        pred_executed = [tuple(d.values()) for d in task.pred_exec_result]
        for exec_result in task.gold_exec_results:
            gold_executed = [tuple(d.values()) for d in exec_result]
            if self._compare(pred_executed, gold_executed) == 1.0:
                return 1.0
        return 0.0
