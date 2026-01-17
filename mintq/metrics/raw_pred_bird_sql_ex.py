from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.db_connector import NL2QDBConnector
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_gold_query
from mintq.schema import NumericOrNull


@metric_registry.register
class RawPredBirdSQLEx:
    name: ClassVar[str] = "raw_pred_bird_sql_ex"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: NL2QDBConnector) -> NumericOrNull:
        # The agent failed to generate a query, or the agent does not record the raw predicted query in extra_info
        if task.extra_pred_info.raw_pred_query is None:
            return 0.0

        raw_pred_query = task.extra_pred_info.raw_pred_query
        gold_query = get_final_gold_query(task)

        # The generated query is not executable
        if raw_pred_query.exec_result.df is None or gold_query.exec_result.df is None:  # type: ignore
            return 0.0

        pred_executed = [row for row in raw_pred_query.exec_result.df.itertuples(index=False, name=None)]  # type: ignore
        gold_executed = [row for row in gold_query.exec_result.df.itertuples(index=False, name=None)]  # type: ignore
        if set(pred_executed) == set(gold_executed):
            return 1.0
        return 0.0
