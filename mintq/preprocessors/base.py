from typing import Any, Protocol, ClassVar
from mintq.db_connector import NL2QDBConnector


class BaseDBPreprocessor(Protocol):
    name: ClassVar[str]

    async def preprocess_async(self, db_connector: NL2QDBConnector) -> Any: ...
