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

        for gold_query in task.gold_queries:
            try:
                await db_connector.run_query_async(gold_query, timeout=self.timeout)
            except Exception as e:
                print(f"Warning: Exception {e} occurred while executing gold queries")
                return 0.0

        return 1.0
