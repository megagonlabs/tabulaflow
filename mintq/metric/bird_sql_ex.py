from mintq.metric.base import NL2QMetric
from mintq.schema import SingleOutputNL2QTask
from mintq.db_connector import SQLiteConnector


class BirdSQLEx(NL2QMetric):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def compute(self, task: SingleOutputNL2QTask, db_connector: SQLiteConnector) -> float:
        try:
            pred_executed = db_connector.run_query(task.pred_query, timeout=self.timeout)
        except Exception:
            return 0.0

        for gold_query in task.gold_queries:
            if task.pred_query == gold_query:
                return 1.0

            try:
                gold_executed = db_connector.run_query(gold_query, timeout=self.timeout)
            except Exception as e:
                print(f"Warning: Exception {e} occurred while executing gold queries")
                continue

            if set(pred_executed) == set(gold_executed):
                return 1.0

        return 0.0
