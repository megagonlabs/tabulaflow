from typing import Any, Protocol, Sequence, Mapping, TypeAlias, Union
import sqlalchemy
from mintq.schema import SQLDialect, NonSQLLanguage, SQLSchema, PropertyGraphSchema, ExecResult, TableRef


class BaseSQLDBConnector(Protocol):
    global_id: str
    schema: SQLSchema
    language: SQLDialect

    def __init__(self, global_id: str, **kwargs: Any): ...

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
    ) -> ExecResult: ...

    async def disconnect_async(self) -> None:
        """Close active connections, releasing any held resources (e.g. file locks).

        The connector remains usable — new connections are created on demand.
        """
        ...

    async def refresh_schema_async(
        self,
        tables: list[TableRef] | None = None,
    ) -> SQLSchema: ...


class BasePropertyGraphDBConnector(Protocol):
    global_id: str
    schema: PropertyGraphSchema
    language: NonSQLLanguage

    def __init__(self, global_id: str, **kwargs: Any): ...

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ExecResult: ...

    async def disconnect_async(self) -> None:
        """Close active connections, releasing any held resources."""
        ...

    async def refresh_schema_async(self) -> PropertyGraphSchema: ...


NL2QDBConnector: TypeAlias = Union[BaseSQLDBConnector, BasePropertyGraphDBConnector]
