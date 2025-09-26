from typing import ClassVar
from mintq.schema import SimpleNL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector
from mintq.registry import metric_registry


@metric_registry.register
class GoldExecutable:
    name: ClassVar[str] = "gold_executable"

    async def compute_async(self, task: SimpleNL2QTaskOutput) -> float:
        if not task.gold_query.exec_result:
            raise ValueError("ExecResult not populated")

        return float(task.gold_query.exec_result.df is not None)
