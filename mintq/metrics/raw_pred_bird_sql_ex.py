import copy
from typing import ClassVar
from mintq.schema import NL2QTaskOutput, SimpleNL2QTaskOutput
from mintq.db_connector import NL2QDBConnector
from mintq.metrics.base import metric_registry
from mintq.metrics.bird_sql_ex import BirdSQLEx
from mintq.schema import NumericOrNull


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
