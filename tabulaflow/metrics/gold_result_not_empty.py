from typing import ClassVar
from tabulaflow.schema import NL2QTaskOutput
from tabulaflow.db_connector import NL2QDBConnector
from tabulaflow.metrics.base import metric_registry
from tabulaflow.metrics.utils import get_final_gold_query


@metric_registry.register
class GoldResultNotEmpty:
    name: ClassVar[str] = "gold_result_not_empty"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: NL2QDBConnector | None = None) -> float:
        gold_query = get_final_gold_query(task)
        return float(gold_query.exec_result.df is not None and len(gold_query.exec_result.df) > 0)  # type: ignore
