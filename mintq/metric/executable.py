from mintq.metric.base import NL2QMetric
from mintq.schema import SingleOutputNL2QTask
from mintq.db_connector import BaseDBConnector


class Executable(NL2QMetric):
    name = "executable"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def compute(self, task: SingleOutputNL2QTask, db_connector: BaseDBConnector) -> float:
        try:
            db_connector.run_query(task.pred_query, timeout=self.timeout)
        except Exception as e:
            print(f"Warning: Exception {e} occurred while executing queries")
            return 0.0

        return 1.0
