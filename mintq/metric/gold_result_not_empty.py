from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class GoldResultNotEmpty:
    name = "gold_result_not_empty"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncDBConnector) -> float:
        for exec_result in task.gold_exec_results:
            if len(exec_result) == 0:
                return 0.0
        return 1.0
