from typing import Any, Protocol, Sequence
import sqlalchemy
import pandas as pd
from mintq.schema import BaseDBSchema, SQLSchema


class BaseAsyncDBConnector(Protocol):
    name: str  # note: for db connectors, name is an instance attribute
    schema: BaseDBSchema

    def __init__(self, name: str, **kwargs: Any): ...

    async def run_query_async(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...


class BaseAsyncSQLDBConnector(Protocol):
    name: str  # note: for db connectors, name is an instance attribute
    schema: SQLSchema

    def __init__(self, name: str, **kwargs: Any): ...

    async def run_query_async(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...

    async def run_statement_async(
        self,
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame: ...
