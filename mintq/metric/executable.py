from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class Executable:
    name = "executable"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncDBConnector) -> float:
        return float(task.pred_exec_result is not None)
