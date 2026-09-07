"""Data connector protocol and shared execution errors."""

from collections.abc import Mapping
import re
from typing import Any, Protocol

from tabulaflow.core.results import ExecResult
from tabulaflow.core.schema import DataSourceSchema, QueryLanguage

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


class DataConnector(Protocol):
    """Structural interface implemented by every live queryable data source."""

    @property
    def global_id(self) -> str:
        """Return the stable connector identity used by caches."""
        ...

    @property
    def schema(self) -> DataSourceSchema:
        """Return the connector's current source schema."""
        ...

    @property
    def backend(self) -> str:
        """Return the concrete backend name."""
        ...

    @property
    def language(self) -> QueryLanguage:
        """Return the query language understood by the connector."""
        ...

    @property
    def read_only(self) -> bool:
        """Return whether mutating operations are blocked."""
        ...

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] = ...,
        timeout: int | None = ...,
    ) -> ExecResult:
        """Execute a query and return rows, graph data, or an error as data."""
        ...

    async def close_async(self) -> None:
        """Permanently close the connector and release held resources."""
        ...

    async def refresh_schema_async(self) -> DataSourceSchema:
        """Re-introspect and return the live source schema."""
        ...
