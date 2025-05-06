import math
from mintq.schema import SingleOutputNL2QTask
from mintq.db_connector import BaseDBConnector
from mintq.metric.base import NL2QMetric


class GoldExecutable(NL2QMetric):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def compute(self, task: SingleOutputNL2QTask, db_connector: BaseDBConnector) -> float:
        if not task.gold_queries:
            return math.nan

        for gold_query in task.gold_queries:
            try:
                db_connector.run_query(gold_query, timeout=self.timeout)
            except Exception as e:
                print(f"Warning: Exception {e} occurred while executing gold queries")
                return 0.0

        return 1.0
