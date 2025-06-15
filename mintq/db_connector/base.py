from typing import Any, Protocol, Sequence, Mapping
import sqlalchemy
import pandas as pd
from mintq.schema import BaseDBSchema, SQLSchema


class BaseAsyncDBConnector(Protocol):
    name: str  # note: for db connectors, name is an instance attribute
    schema: BaseDBSchema

    def __init__(self, name: str, **kwargs: Any): ...

    async def run_query_async(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30
    ) -> list[tuple[Any, ...]]: ...


class BaseAsyncSQLDBConnector(Protocol):
    name: str  # note: for db connectors, name is an instance attribute
    schema: SQLSchema

    def __init__(self, name: str, **kwargs: Any): ...

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...
