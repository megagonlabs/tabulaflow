from typing import Any, Protocol, ClassVar
from mintq.db_connector import BaseAsyncDBConnector


class BaseAsyncMetadataSynthesizer(Protocol):
    name: ClassVar[str]

    async def run_async(self, db_connector: BaseAsyncDBConnector) -> Any: ...
