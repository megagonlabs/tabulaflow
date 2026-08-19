from typing import ClassVar
from tabulaflow.research.types import NL2QTaskOutput
from tabulaflow.data import DBConnector
from tabulaflow.research.metrics.base import metric_registry
from tabulaflow.research.metrics.utils import get_final_pred_query


@metric_registry.register
class PredSuccess:
    name: ClassVar[str] = "pred_success"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: DBConnector | None = None) -> float:
        pred_query = get_final_pred_query(task)
        return float(pred_query is not None)
