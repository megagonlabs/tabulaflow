from typing import ClassVar
from tabulaflow.research.types import NL2QTaskOutput
from tabulaflow.data import DataConnector
from tabulaflow.research.metrics.registry import metric_registry
from tabulaflow.research.metrics.utils import get_final_pred_query


@metric_registry.register
class Executable:
    name: ClassVar[str] = "executable"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: DataConnector | None = None) -> float:
        pred_query = get_final_pred_query(task)
        if pred_query is None:
            return 0.0

        assert pred_query.exec_result is not None
        return float(pred_query.exec_result.df is not None)
