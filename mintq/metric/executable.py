from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class Executable:
    name = "executable"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncDBConnector) -> float:
        try:
            await db_connector.run_query_async(task.pred_query, timeout=self.timeout)
        except Exception as e:
            print(f"Warning: Exception {e} occurred while executing queries")
            return 0.0

        return 1.0
