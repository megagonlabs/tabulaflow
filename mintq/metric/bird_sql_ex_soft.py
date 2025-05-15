from itertools import combinations
from mintq.db_connector import SQLiteConnector
from mintq.metric.base import NL2QMetric
from mintq.schema import SingleOutputNL2QTask


class BirdSQLExSoft(NL2QMetric):
    name = "bird_sql_ex_soft"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def _compare(self, pred_executed: list[tuple], gold_executed: list[tuple]) -> float:
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

    def compute(self, task: SingleOutputNL2QTask, db_connector: SQLiteConnector) -> float:
        if not task.gold_exec_results and not task.gold_queries:
            raise ValueError("No gold queries or gold execution results provided")

        try:
            pred_executed = db_connector.run_query(task.pred_query, timeout=self.timeout)
        except Exception:
            return 0.0

        if task.gold_exec_results:
            for exec_result in task.gold_exec_results:
                keys = list(exec_result[0])
                gold_executed = [tuple(row[key] for key in keys) for row in exec_result]
                if self._compare(pred_executed, gold_executed) == 1.0:
                    return 1.0
            return 0.0

        for gold_query in task.gold_queries:
            if task.pred_query == gold_query:
                return 1.0

            try:
                gold_executed = db_connector.run_query(gold_query, timeout=self.timeout)
            except Exception as e:
                print(f"Warning: Exception {e} occurred while executing gold queries")
                continue

            if self._compare(pred_executed, gold_executed) == 1.0:
                return 1.0
        return 0.0
