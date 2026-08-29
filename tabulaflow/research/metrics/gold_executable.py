from typing import ClassVar
from tabulaflow.research.types import NL2QTaskOutput
from tabulaflow.data import DBConnector
from tabulaflow.research.metrics.registry import metric_registry
from tabulaflow.research.metrics.utils import get_final_gold_query


@metric_registry.register
class GoldExecutable:
    name: ClassVar[str] = "gold_executable"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: DBConnector | None = None) -> float:
        gold_query = get_final_gold_query(task)
        assert gold_query.exec_result is not None
        return float(gold_query.exec_result.df is not None)
