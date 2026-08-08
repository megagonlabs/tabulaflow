"""Serializable chat-turn result models."""

from __future__ import annotations

from typing import Annotated, Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.outputs import ArtifactDef
from tabulaflow.core.types import GraphView, Usage


SelectionValue = str | int | float | bool


class ControlChoice(BaseModel):
    """One option in a finite answer control."""

    id: str
    label: str


class ChoiceControl(BaseModel):
    """Answer-level finite-choice control."""

    kind: Literal["choice"] = "choice"
    id: str
    label: str
    choices: list[ControlChoice]


class SliderControl(BaseModel):
    """Answer-level numeric slider control."""

    kind: Literal["slider"] = "slider"
    id: str
    label: str
    min: float
    max: float
    step: float
    default: float
    unit: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "SliderControl":
        if self.max <= self.min:
            raise ValueError("slider max must be greater than min")
        if self.step <= 0:
            raise ValueError("slider step must be positive")
        if not self.min <= self.default <= self.max:
            raise ValueError("slider default must be between min and max")
        return self


AnswerControl = Annotated[ChoiceControl | SliderControl, Field(discriminator="kind")]


class AnswerPanel(BaseModel):
    """Answer-level controls and initial selection."""

    controls: list[AnswerControl] = Field(default_factory=list)
    default_selection: dict[str, SelectionValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fill_default_selection(self) -> "AnswerPanel":
        if not self.default_selection:
            for control in self.controls:
                if isinstance(control, ChoiceControl) and control.choices:
                    self.default_selection[control.id] = control.choices[0].id
                elif isinstance(control, SliderControl):
                    self.default_selection[control.id] = control.default
        return self


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
    artifacts: list[ArtifactDef] = Field(default_factory=list)
    primary_artifact_index: int | None = 0
    usage: Usage | None = None
    panel: AnswerPanel | None = None

    @property
    def primary_artifact(self) -> ArtifactDef | None:
        if not self.artifacts:
            return None
        if self.primary_artifact_index is None:
            return None
        if self.primary_artifact_index < 0 or self.primary_artifact_index >= len(self.artifacts):
            return None
        return self.artifacts[self.primary_artifact_index]
