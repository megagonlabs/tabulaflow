from typing import Any, Protocol, Sequence, Mapping, TypeAlias
import sqlalchemy
from mintq.schema import SQLSchema, ExecResult


class BaseSQLDBConnector(Protocol):
    global_id: str
    schema: SQLSchema

    def __init__(self, global_id: str, **kwargs: Any): ...

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
    ) -> ExecResult: ...


NL2QDBConnector: TypeAlias = BaseSQLDBConnector
