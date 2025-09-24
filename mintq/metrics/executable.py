from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class Executable:
    name = "executable"

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncDBConnector) -> float:
        if not task.pred_query.exec_result:
            raise ValueError("ExecResult not populated")

        return float(task.pred_query.exec_result.df is not None)
