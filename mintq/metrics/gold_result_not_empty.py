from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class GoldResultNotEmpty:
    name = "gold_result_not_empty"

    async def compute_async(self, task: SimpleNL2QTaskOutput, db_connector: BaseAsyncDBConnector) -> float:
        return float(task.gold_query.exec_result.df is not None and len(task.gold_query.exec_result.df) > 0)
