from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector
from mintq.registry import metric_registry


@metric_registry.register
class GoldResultNotEmpty:
    name = "gold_result_not_empty"

    async def compute_async(self, task: SimpleNL2QTaskOutput) -> float:
        if not task.gold_query.exec_result:
            raise ValueError("ExecResult not populated")

        return float(task.gold_query.exec_result.df is not None and len(task.gold_query.exec_result.df) > 0)
