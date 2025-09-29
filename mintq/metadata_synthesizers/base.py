from typing import Any, Protocol, ClassVar
from mintq.db_connector import NL2QDBConnector


class BaseAsyncMetadataSynthesizer(Protocol):
    name: ClassVar[str]

    async def run_async(self, db_connector: NL2QDBConnector) -> Any: ...
