import copy
from typing import ClassVar
from tabulaflow.research.types import NL2QTaskOutput, SimpleNL2QTaskOutput
from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.research.metrics.base import metric_registry
from tabulaflow.research.metrics.bird_sql_ex import BirdSQLEx
from tabulaflow.core.types import NumericOrNull


@metric_registry.register
class RawPredBirdSQLEx:
    name: ClassVar[str] = "raw_pred_bird_sql_ex"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: NL2QDBConnector | None = None) -> NumericOrNull:
        assert isinstance(task, SimpleNL2QTaskOutput)
        bird_sql_ex = BirdSQLEx()
        task = copy.deepcopy(task)
        task.pred_query = task.extra_pred_info.raw_pred_query
        return await bird_sql_ex.compute_async(task, db_connector)
