from typing import Any, Protocol, ClassVar
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import SQLSchema


class BaseDBPreprocessor(Protocol):
    name: ClassVar[str]

    async def preprocess_async(self, db_connector: BaseSQLDBConnector) -> Any: ...


class BaseSchemaCompressor(Protocol):
    async def preprocess_async(self, db_connector: BaseSQLDBConnector) -> SQLSchema: ...
