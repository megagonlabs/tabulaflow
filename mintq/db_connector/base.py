from typing import Any, Protocol, Sequence, Mapping
import sqlalchemy
from mintq.schema import BaseDBSchema, SQLSchema, ExecResult


class BaseAsyncDBConnector(Protocol):
    global_id: str
    schema: BaseDBSchema

    def __init__(self, global_id: str, **kwargs: Any): ...

    async def run_query_async(
        self, query: str, parameters: Sequence[Any] = (), timeout: int | None = None
    ) -> ExecResult: ...


class BaseAsyncSQLDBConnector(Protocol):
    global_id: str
    schema: SQLSchema

    def __init__(self, global_id: str, **kwargs: Any): ...

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
    ) -> ExecResult: ...
