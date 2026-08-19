import copy
from typing import ClassVar
from tabulaflow.research.types import NL2QTaskOutput, NumericOrNull, SimpleNL2QTaskOutput
from tabulaflow.data import DBConnector
from tabulaflow.research.metrics.base import metric_registry
from tabulaflow.research.metrics.simple_ex import SimpleEx


@metric_registry.register
class RawPredSimpleEx:
    name: ClassVar[str] = "raw_pred_simple_ex"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    def __init__(self, abs_tol: float = 1e-2, ignore_repetitions: bool = True):
        self.abs_tol = abs_tol
        self.ignore_repetitions = ignore_repetitions

    async def compute_async(self, task: NL2QTaskOutput, db_connector: DBConnector | None = None) -> NumericOrNull:
        assert isinstance(task, SimpleNL2QTaskOutput)
        task = copy.deepcopy(task)
        task.pred_query = task.extra_pred_info.raw_pred_query
        simple_ex = SimpleEx(abs_tol=self.abs_tol, ignore_repetitions=self.ignore_repetitions)
        return await simple_ex.compute_async(task, db_connector)
