from typing import Protocol, ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.db_connector import BaseDBConnector


class BaseNL2QMetric(Protocol):
    name: ClassVar[str]

    def compute(self, task: NL2QTaskOutput, db_connector: BaseDBConnector) -> float: ...
