from typing import Any, Protocol, ClassVar
from mintq.db_connector import BaseDBConnector


class BaseMetadataSynthesizer(Protocol):
    name: ClassVar[str]

    def run(self, db_connector: BaseDBConnector) -> Any: ...
