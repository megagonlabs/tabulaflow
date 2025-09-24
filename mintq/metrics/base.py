from typing import Protocol, ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.db_connector import BaseAsyncDBConnector


class BaseAsyncNL2QMetric(Protocol):
    name: ClassVar[str]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: BaseAsyncDBConnector) -> float: ...
