from mintq.schema import SingleOutputBaseNL2QTask
from mintq.db_connector import BaseDBConnector
from mintq.metric.base import NL2QMetric


class GoldExecutable(NL2QMetric):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def compute(self, task: SingleOutputBaseNL2QTask, db_connector: BaseDBConnector) -> float:
        try:
            db_connector.run_query(task.gold_query, timeout=self.timeout)
        except Exception as e:
            print(f"Warning: Exception {e} occurred while executing queries")
            return 0.0

        return 1.0
