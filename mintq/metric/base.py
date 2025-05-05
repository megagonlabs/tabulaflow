from abc import ABC, abstractmethod
from mintq.schema import NL2QTask
from mintq.db_connector import BaseDBConnector


class NL2QMetric(ABC):
    @abstractmethod
    def compute(self, task: NL2QTask, db_connector: BaseDBConnector) -> float:
        pass
