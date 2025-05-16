from abc import ABC, abstractmethod
from mintq.schema import NL2QTaskOutput
from mintq.db_connector import BaseDBConnector


class NL2QMetric(ABC):
    name: str

    @abstractmethod
    def compute(self, task: NL2QTaskOutput, db_connector: BaseDBConnector) -> float:
        pass
