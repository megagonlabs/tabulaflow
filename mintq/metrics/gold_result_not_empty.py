from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_gold_query


@metric_registry.register
class GoldResultNotEmpty:
    name: ClassVar[str] = "gold_result_not_empty"

    async def compute_async(self, task: NL2QTaskOutput) -> float:
        gold_query = get_final_gold_query(task)
        return float(gold_query.exec_result.df is not None and len(gold_query.exec_result.df) > 0)  # type: ignore
