from typing import Any, ClassVar, Literal, Protocol, Sequence, Mapping, TypeAlias, Union
import sqlalchemy
from mintq.schema import SQLDialect, NonSQLLanguage, SQLSchema, PropertyGraphSchema, ExecResult, TableRef


class BaseSQLDBConnector(Protocol):
    connector_type: ClassVar[Literal["sql"]]
    global_id: str
    schema: SQLSchema

    # Read-only — ``SQLConnector`` derives this from ``schema.dialect``
    # via ``@property``.  A plain class attribute on the implementation
    # also satisfies a property-typed Protocol member.
    @property
    def language(self) -> SQLDialect: ...

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
    connector_type: ClassVar[Literal["property_graph"]]
    global_id: str
    schema: PropertyGraphSchema

    @property
    def language(self) -> NonSQLLanguage: ...

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
