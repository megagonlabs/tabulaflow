import math
from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class GoldExecutable:
    name = "gold_executable"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncDBConnector) -> float:
        if not task.gold_queries:
            return math.nan

        if len(task.gold_queries) == len(task.gold_exec_results):
            return 1.0
        else:
            return 0.0
