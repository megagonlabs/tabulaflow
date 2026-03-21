from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.db_connector import NL2QDBConnector
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_pred_query


@metric_registry.register
class Executable:
    name: ClassVar[str] = "executable"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: NL2QDBConnector | None = None) -> float:
        pred_query = get_final_pred_query(task)
        if pred_query is None:
            return 0.0

        return float(pred_query.exec_result.df is not None)  # type: ignore
