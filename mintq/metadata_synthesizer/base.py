from abc import ABC, abstractmethod
from mintq.db_connector import BaseDBConnector
from typing import Any

class BaseMetadataSynthesizer(ABC):
    @abstractmethod
    def run(self, db_connector: BaseDBConnector) -> Any:
        pass
