from mintq.metric.base import NL2QMetric
from mintq.schema import SingleOutputNL2QTask
from mintq.db_connector import BaseDBConnector


class GoldResultNotEmpty(NL2QMetric):
    name = "gold_result_not_empty"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def compute(self, task: SingleOutputNL2QTask, db_connector: BaseDBConnector) -> float:
        if not task.gold_exec_results and not task.gold_queries:
            raise ValueError("No gold queries or gold execution results provided")

        if task.gold_exec_results:
            for exec_result in task.gold_exec_results:
                if len(exec_result) == 0:
                    return 0.0
            return 1.0

        for gold_query in task.gold_queries:
            try:
                gold_executed = db_connector.run_query(gold_query, timeout=self.timeout)
            except Exception as e:
                print(f"Warning: Exception {e} occurred while executing gold queries")
                return 0.0

            if len(gold_executed) == 0:
                return 0.0

        return 1.0
