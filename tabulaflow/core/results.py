from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tabulaflow.core.serialization import SerializableDataFrame


class ErrorInfo(BaseModel):
    exc_type: str
    message: str


class GraphResultNode(BaseModel):
    """Node in a generic query-result graph view."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str | None = None
    group: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResultEdge(BaseModel):
    """Edge in a generic query-result graph view."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    source: str
    target: str
    label: str | None = None
    directed: bool = True
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResult(BaseModel):
    """Generic node-link graph view attached to a query result."""

    nodes: list[GraphResultNode]
    edges: list[GraphResultEdge]


class ExecResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: SerializableDataFrame = None
    graph: GraphResult | None = None
    df_is_truncated: bool = False
    """True if the df is truncated, e.g. when the result is too large"""
    affected_rows: int | None = None
    """Rows matched/affected by a single-statement DML (INSERT/UPDATE/DELETE/MERGE),
    when the driver reports it. ``None`` for SELECT, DDL, multi-statement scripts,
    and drivers that don't surface a count. ``0`` means the statement ran but
    matched no rows (e.g. a WHERE that hit nothing) — distinct from ``None``."""
    error: ErrorInfo | None = None
    latency_seconds: float | None = None

    @property
    def succeeded(self) -> bool:
        """Whether the statement executed without error.

        This is the success signal — ``error is None``. It is independent of
        whether the statement produced rows: a successful ``CREATE``/``UPDATE``
        has ``succeeded=True`` but no result set (``df is None``). A result set
        is ``df is not None`` — check that directly."""
        return self.error is None

    @model_validator(mode="after")
    def validate_df_or_error(self) -> "ExecResult":
        # Success is ``error is None``; a result set is ``df is not None``. These
        # are independent: a successful non-row statement (DDL/DML) has neither a
        # df nor an error. Only a df *and* an error together is contradictory.
        if self.df is not None and self.error is not None:
            raise ValueError("ExecResult must not carry both df and error")
        return self
