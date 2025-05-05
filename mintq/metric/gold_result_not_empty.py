from mintq.metric.base import NL2QMetric
from mintq.schema import SingleOutputBaseNL2QTask
from mintq.db_connector import BaseDBConnector


class GoldResultNotEmpty(NL2QMetric):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def compute(self, task: SingleOutputBaseNL2QTask, db_connector: BaseDBConnector) -> float:
        try:
            gold_executed = db_connector.run_query(task.gold_query, timeout=self.timeout)
        except Exception as e:
            print(f"Warning: Exception {e} occurred while executing queries")
            return 0.0

        if len(gold_executed) == 0:
            return 0.0

        return 1.0
