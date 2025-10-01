from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.metrics.base import metric_registry


@metric_registry.register
class Executable:
    name: ClassVar[str] = "executable"

    async def compute_async(self, task: NL2QTaskOutput) -> float:
        if task.task_type == "simple":
            pred_query = task.pred_query
        elif task.task_type == "ambig":
            pred_query = task.pred_intended_query
        else:
            raise ValueError(f"Invalid task type: {task.task_type}")

        if not pred_query.exec_result:
            raise ValueError("ExecResult not populated")

        return float(pred_query.exec_result.df is not None)
