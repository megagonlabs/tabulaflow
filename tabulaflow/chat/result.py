"""Serializable chat-turn result models."""

from __future__ import annotations

from typing import Annotated, Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.outputs import OutputSpec
from tabulaflow.core.types import GraphView, Usage


SelectionValue = str | int | float | bool


class ResolvedTableArtifact(BaseModel):
    """Display-ready table artifact."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["table"] = "table"
    record_id: str
    label: str | None
    query: str | None
    df: pd.DataFrame | None
    graph: GraphView | None = None
    query_lexer: str = "sql"

    @field_serializer("df", when_used="always")
    def _serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def _deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)


class ResolvedChartArtifact(BaseModel):
    """Display-ready chart artifact."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["chart"] = "chart"
    chart_id: str
    label: str | None
    chart_spec: dict[str, Any]
    record_id: str
    query: str | None
    df: pd.DataFrame | None
    query_lexer: str = "sql"

    @field_serializer("df", when_used="always")
    def _serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def _deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)


class ResolvedMapArtifact(BaseModel):
    """Display-ready map artifact."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["map"] = "map"
    map_id: str
    label: str | None
    map_spec: dict[str, Any]
    sources: dict[str, pd.DataFrame]

    @field_serializer("sources", when_used="always")
    def _serialize_sources(self, sources: dict[str, pd.DataFrame]) -> dict[str, Any]:
        return {rid: _serialize_dataframe(df) for rid, df in sources.items()}

    @field_validator("sources", mode="before")
    @classmethod
    def _deserialize_sources(cls, v: dict[str, Any]) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for rid, df in (v or {}).items():
            deserialized = _deserialize_dataframe(df)
            if deserialized is not None:
                out[rid] = deserialized
        return out


class ResolvedGraphArtifact(BaseModel):
    """Display-ready graph artifact."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["graph"] = "graph"
    graph_id: str
    label: str | None
    graph: GraphView
    layout: Literal["force", "layered", "tree"] = "force"


class ArtifactPlaceholder(BaseModel):
    """Placeholder for a source that does not apply to the selected controls."""

    kind: Literal["placeholder"] = "placeholder"
    label: str | None
    message: str


ResolvedArtifact = Annotated[
    ResolvedTableArtifact | ResolvedChartArtifact | ResolvedMapArtifact | ResolvedGraphArtifact | ArtifactPlaceholder,
    Field(discriminator="kind"),
]


class ChatResult(BaseModel):
    """Logical result of one chat turn."""

    text: str
    output: OutputSpec = Field(default_factory=OutputSpec)
    usage: Usage | None = None
