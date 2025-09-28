from typing import ClassVar
from mintq.schema import SimpleNL2QTaskOutput
from mintq.metrics.base import metric_registry


@metric_registry.register
class Executable:
    name: ClassVar[str] = "executable"

    async def compute_async(self, task: SimpleNL2QTaskOutput) -> float:
        if not task.pred_query.exec_result:
            raise ValueError("ExecResult not populated")

        return float(task.pred_query.exec_result.df is not None)
