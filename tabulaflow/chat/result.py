"""The chat-turn result view-model — the ``Finished`` event payload.

Pydantic models (consistent with the rest of the data layer in ``core.types`` /
``research.types``), so the whole chat⇄frontend contract is wire-serializable.
The DataFrame field reuses the same Arrow serializer as ``core.ExecResult``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.types import GraphView, Usage
from tabulaflow.toolhub import Dimension


class ChatResultRecord(BaseModel):
    """Display-ready data for one referenced query result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["record"] = "record"
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


class ChatResultChart(BaseModel):
    """Display-ready data for one cited chart artifact.

    A standalone chart drawn from a single query result. Carries the source
    record's rows and query alongside the ``chart_spec`` so the card offers
    chart, data, and query views.
    """

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


class ChatResultMap(BaseModel):
    """Display-ready data for one cited map artifact.

    A standalone, map-only card assembled from one or more query results. Its
    normalized ``map_spec`` layers each name the ``source`` record they read from;
    ``sources`` holds those records' DataFrames keyed by record id.
    """

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


class ChatResultGraph(BaseModel):
    """Display-ready data for one cited graph artifact."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: Literal["graph"] = "graph"
    graph_id: str
    label: str | None
    graph: GraphView
    layout: Literal["force", "layered", "tree"] = "force"


class ChatResultPlaceholder(BaseModel):
    """Stands in for a card at a combination its query never ran.

    ``message`` is derived from the panel's own labels (e.g. "only applies when
    Time period = Last completed quarter"), so it cannot contradict the coordinates.
    """

    kind: Literal["placeholder"] = "placeholder"
    label: str | None
    message: str


# A cited artifact is either a query result (record) or a standalone chart, map,
# or graph, discriminated by ``kind``; ``ChatResult.artifacts`` holds them in
# citation order.
ChatResultArtifact = Annotated[
    ChatResultRecord | ChatResultChart | ChatResultMap | ChatResultGraph, Field(discriminator="kind")
]

# Inside a panel a card may also be a placeholder, for a combination its query never
# ran.  Kept out of ``ChatResultArtifact`` so the ordinary render path — which every
# frontend already implements — never has to consider it.
ChatResultCard = Annotated[
    ChatResultRecord | ChatResultChart | ChatResultMap | ChatResultGraph | ChatResultPlaceholder,
    Field(discriminator="kind"),
]


class ChatResultCombination(BaseModel):
    """One point of the interpretation space: a choice per dimension, and the cards there.

    ``artifacts`` carries the same labels in the same order at every combination — only
    their contents change as the user switches.
    """

    selection: dict[str, str]
    artifacts: list[ChatResultCard] = Field(default_factory=list)


class ChatResultPanel(BaseModel):
    """The turn's interpretation space: what the user may switch between, and the results.

    ``combinations`` is ordered so the first entry is the first choice of every
    dimension — the reading the answer text describes.
    """

    dimensions: list[Dimension]
    combinations: list[ChatResultCombination]


class ChatResult(BaseModel):
    """The complete result of a single chat turn (the ``Finished`` payload)."""

    text: str
    artifacts: list[ChatResultArtifact] = Field(default_factory=list)
    primary_artifact_index: int | None = 0
    usage: Usage | None = None
    # Present when the turn offered interpretations. ``artifacts`` then mirrors the
    # panel's first combination, so a frontend with no panel support still renders
    # the reading the answer describes.
    panel: ChatResultPanel | None = None

    @property
    def primary_artifact(self) -> ChatResultArtifact | None:
        if not self.artifacts:
            return None
        if self.primary_artifact_index is None:
            return None
        if self.primary_artifact_index < 0 or self.primary_artifact_index >= len(self.artifacts):
            return None
        return self.artifacts[self.primary_artifact_index]
