"""Database connector protocols and shared execution errors."""

from collections.abc import Mapping, Sequence
import re
from typing import Any, ClassVar, Literal, Protocol, TypeAlias

import pandas as pd
from sqlalchemy.sql import Executable

from tabulaflow.core.results import ExecResult
from tabulaflow.core.schema import GraphQueryLanguage, PropertyGraphSchema, SQLDialect, SQLSchema, TableRef

DataFrameWriteMode: TypeAlias = Literal["create", "append", "replace_rows", "replace_table"]

_GLOBAL_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,179}")


def validate_global_id(global_id: str) -> str:
    """Validate and return a globally unique, filename-safe connector ID."""
    if _GLOBAL_ID_PATTERN.fullmatch(global_id) is None:
        raise ValueError(
            "global_id must be 1-180 characters, start with a letter or digit, "
            "and contain only letters, digits, '.', '_', '+', or '-'"
        )
    return global_id


class ResultTooLargeError(RuntimeError):
    """A query produced more rows than may be materialized safely."""

    def __init__(self, max_rows: int) -> None:
        super().__init__(f"Query returned more than {max_rows:,} rows; add a LIMIT, filter, or aggregation")


class SQLConnectorProtocol(Protocol):
    """Structural interface implemented by SQL database connectors."""

    connector_type: ClassVar[Literal["sql"]]
    global_id: str
    schema: SQLSchema

    @property
    def backend(self) -> str:
        """Return the concrete SQL database backend name."""
        ...

    @property
    def language(self) -> SQLDialect:
        """Return the SQL dialect understood by the connector."""
        ...

    async def run_query_async(
        self,
        query: str | Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = ...,
    ) -> ExecResult:
        """Execute a SQL statement and return rows or an error as data."""
        ...

    async def close_async(self) -> None:
        """Permanently close the connector and release held resources."""
        ...

    async def release_connections_async(self) -> None:
        """Release pooled connections while keeping the connector reusable."""
        ...

    async def refresh_schema_async(
        self,
        tables: list[TableRef] | None = None,
    ) -> SQLSchema:
        """Re-introspect all or selected tables and return the live schema."""
        ...

    async def write_dataframe_async(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema_name: str | None = None,
        mode: DataFrameWriteMode = "create",
    ) -> int:
        """Write rows according to ``mode`` and return the number written."""
        ...


class PropertyGraphConnectorProtocol(Protocol):
    """Structural interface implemented by property-graph connectors."""

    connector_type: ClassVar[Literal["property_graph"]]
    global_id: str
    schema: PropertyGraphSchema

    @property
    def backend(self) -> str:
        """Return the graph database backend name."""
        ...

    @property
    def language(self) -> GraphQueryLanguage:
        """Return the query language understood by the connector."""
        ...

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: int | None = ...,
    ) -> ExecResult:
        """Execute a graph query and return tabular/graph data or an error."""
        ...

    async def close_async(self) -> None:
        """Permanently close the connector and release held resources."""
        ...

    async def refresh_schema_async(self) -> PropertyGraphSchema:
        """Re-introspect and return the live property-graph schema."""
        ...


DBConnector: TypeAlias = SQLConnectorProtocol | PropertyGraphConnectorProtocol
"""Any live SQL or property-graph connector."""
