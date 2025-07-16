from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncSQLDBConnector


class BirdSQLEx:
    name = "bird_sql_ex"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncSQLDBConnector) -> float:
        if task.pred_exec_result is None:
            return 0.0

        pred_executed = [tuple(d.values()) for d in task.pred_exec_result]
        for exec_result in task.gold_exec_results:
            gold_executed = [tuple(d.values()) for d in exec_result]
            if set(pred_executed) == set(gold_executed):
                return 1.0
        return 0.0
