"""Database connector protocols and shared execution errors."""

from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Literal, Protocol, TypeAlias

from sqlalchemy.sql import Executable

from tabulaflow.core import ExecResult, NonSQLLanguage, PropertyGraphSchema, SQLDialect, SQLSchema, TableRef


class ResultTooLargeError(RuntimeError):
    """A query produced more rows than may be materialized safely."""

    def __init__(self, max_rows: int) -> None:
        super().__init__(f"Query returned more than {max_rows:,} rows; add a LIMIT, filter, or aggregation")


class SQLConnectorProtocol(Protocol):
    connector_type: ClassVar[Literal["sql"]]
    global_id: str
    schema: SQLSchema

    @property
    def language(self) -> SQLDialect: ...

    async def run_query_async(
        self,
        query: str | Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = ...,
    ) -> ExecResult: ...

    async def disconnect_async(self) -> None:
        """Close active connections and release held resources."""
        ...

    async def refresh_schema_async(
        self,
        tables: list[TableRef] | None = None,
    ) -> SQLSchema: ...


class PropertyGraphConnectorProtocol(Protocol):
    connector_type: ClassVar[Literal["property_graph"]]
    global_id: str
    schema: PropertyGraphSchema

    @property
    def backend(self) -> str: ...

    @property
    def language(self) -> NonSQLLanguage: ...

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: int | None = ...,
    ) -> ExecResult: ...

    async def disconnect_async(self) -> None:
        """Close active connections and release held resources."""
        ...

    async def refresh_schema_async(self) -> PropertyGraphSchema: ...


DBConnector: TypeAlias = SQLConnectorProtocol | PropertyGraphConnectorProtocol
