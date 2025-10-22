from typing import Any, Protocol, ClassVar
from mintq.db_connector import NL2QDBConnector
from mintq.schema import SQLSchema


class BaseAsyncMetadataSynthesizer(Protocol):
    name: ClassVar[str]

    async def run_async(self, db_connector: NL2QDBConnector) -> Any: ...


class BaseSchemaCompressor(Protocol):
    async def run_async(self, schema: SQLSchema) -> SQLSchema: ...
