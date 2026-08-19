"""Database execution result models."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tabulaflow.core.serialization import SerializableDataFrame


class ErrorInfo(BaseModel):
    """Exception details returned as part of an execution result."""

    exc_type: str
    message: str


class GraphResultNode(BaseModel):
    """Node in a graph-shaped query result."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str | None = None
    group: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResultEdge(BaseModel):
    """Edge in a graph-shaped query result."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    source: str
    target: str
    label: str | None = None
    directed: bool = True
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResult(BaseModel):
    """Complete node-link graph derived from a query within connector limits."""

    nodes: list[GraphResultNode]
    edges: list[GraphResultEdge]


class ExecResult(BaseModel):
    """Outcome of executing one database statement.

    A successful statement may have no payload, as with DDL.

    Attributes:
        df: Complete tabular result for a row-returning query.
        graph: Best-effort complete graph representation attached to a tabular
            result, or None when no graph is derived within connector limits.
        affected_rows: Rows affected by successful non-row DML, when reported.
        error: Failure details; mutually exclusive with successful payloads.
        latency_seconds: Elapsed execution time, when measured.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: SerializableDataFrame | None = None
    graph: GraphResult | None = None
    affected_rows: int | None = Field(default=None, ge=0)
    error: ErrorInfo | None = None
    latency_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        has_result = self.df is not None or self.graph is not None
        if self.error is not None and (has_result or self.affected_rows is not None):
            raise ValueError("an error cannot accompany a result or affected-row count")
        if has_result and self.affected_rows is not None:
            raise ValueError("a result cannot carry an affected-row count")
        if self.graph is not None and self.df is None:
            raise ValueError("a graph result requires a tabular result")
        return self
