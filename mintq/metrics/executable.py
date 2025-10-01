from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_pred_query


@metric_registry.register
class Executable:
    name: ClassVar[str] = "executable"

    async def compute_async(self, task: NL2QTaskOutput) -> float:
        pred_query = get_final_pred_query(task)
        return float(pred_query.exec_result.df is not None)
