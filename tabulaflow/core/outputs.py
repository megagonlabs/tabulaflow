"""Pure output specification models.

These models describe an interactive output without executing anything. Runtime
state such as source caches, connector access, and materialized DataFrames
belongs outside ``core``.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


SelectionValue: TypeAlias = str | int | float | bool
ParameterId: TypeAlias = str
SourceId: TypeAlias = str
ArtifactId: TypeAlias = str
ResultId: TypeAlias = str
SelectionKey: TypeAlias = str
Selection: TypeAlias = dict[ParameterId, SelectionValue]


class ChoiceOption(BaseModel):
    """One finite parameter option."""

    id: str
    label: str


class ChoiceParameter(BaseModel):
    """Finite output parameter."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["choice"] = "choice"
    id: ParameterId
    label: str
    choices: list[ChoiceOption] = Field(min_length=1)


class NumberParameter(BaseModel):
    """Numeric output parameter, optionally rendered as a slider."""

    kind: Literal["number"] = "number"
    id: ParameterId
    label: str
    min: float
    max: float
    step: float
    default: float
    display: Literal["slider", "input"] = "slider"
    unit: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "NumberParameter":
        if self.max <= self.min:
            raise ValueError("number parameter max must be greater than min")
        if self.step <= 0:
            raise ValueError("number parameter step must be positive")
        if not self.min <= self.default <= self.max:
            raise ValueError("number parameter default must be between min and max")
        return self


ParameterDef = Annotated[ChoiceParameter | NumberParameter, Field(discriminator="kind")]


class FixedResultSource(BaseModel):
    """Source that always resolves to one materialized result."""

    kind: Literal["fixed"] = "fixed"
    id: SourceId
    result_id: ResultId


class ParameterizedSource(BaseModel):
    """Source that materializes/cache results under a source-local selection."""

    kind: Literal["parameterized"] = "parameterized"
    id: SourceId
    parameter_ids: list[ParameterId]
    db_alias: str
    query_template: str


SourceDef = Annotated[FixedResultSource | ParameterizedSource, Field(discriminator="kind")]


class ResultMetadata(BaseModel):
    """Metadata for a concrete materialized result; data lives in runtime storage."""

    id: ResultId
    db_alias: str
    query: str
    connector_type: Literal["sql", "property_graph"] = "sql"
    selection: Selection = Field(default_factory=dict)
    row_count: int | None = None
    columns: list[str] | None = None
    latency_seconds: float | None = None


class TableView(BaseModel):
    """Tabular view over one source."""

    kind: Literal["table"] = "table"
    source: SourceId


class ChartView(BaseModel):
    """Chart view over one source."""

    kind: Literal["chart"] = "chart"
    source: SourceId
    spec: dict[str, Any]


class MapView(BaseModel):
    """Map view over one or more sources."""

    kind: Literal["map"] = "map"
    sources: list[SourceId]
    spec: dict[str, Any]


class GraphViewSpec(BaseModel):
    """Graph view over one or more sources."""

    kind: Literal["graph"] = "graph"
    sources: list[SourceId]
    spec: dict[str, Any]


ViewDef = Annotated[TableView | ChartView | MapView | GraphViewSpec, Field(discriminator="kind")]


class ArtifactSpec(BaseModel):
    """Display artifact: identity, label, and view intent."""

    id: ArtifactId
    label: str | None = None
    view: ViewDef


class OutputSpec(BaseModel):
    """Complete declarative contract for an interactive output."""

    parameters: list[ParameterDef] = Field(default_factory=list)
    sources: list[SourceDef] = Field(default_factory=list)
    artifacts: list[ArtifactSpec] = Field(default_factory=list)
    default_selection: Selection = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_spec(self) -> "OutputSpec":
        parameter_ids = [parameter.id for parameter in self.parameters]
        source_ids = [source.id for source in self.sources]
        artifact_ids = [artifact.id for artifact in self.artifacts]
        _require_unique(parameter_ids, "parameter ids")
        _require_unique(source_ids, "source ids")
        _require_unique(artifact_ids, "artifact ids")

        defaults = default_selection(self.parameters)
        defaults.update(self.default_selection)
        self.default_selection = defaults
        parameter_by_id = {parameter.id: parameter for parameter in self.parameters}
        for key, value in self.default_selection.items():
            parameter = parameter_by_id.get(key)
            if parameter is None:
                raise ValueError(f"default selection references unknown parameter {key!r}")
            validate_parameter_value(parameter, value)

        for source in self.sources:
            if isinstance(source, ParameterizedSource):
                for parameter_id in source.parameter_ids:
                    if parameter_id not in parameter_by_id:
                        raise ValueError(f"source {source.id!r} references unknown parameter {parameter_id!r}")

        known_sources = set(source_ids)
        for artifact in self.artifacts:
            for source_id in _view_source_ids(artifact.view):
                if source_id not in known_sources:
                    raise ValueError(f"artifact {artifact.id!r} references unknown source {source_id!r}")
        return self


def _require_unique(values: Sequence[str], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must be unique")


def parameter_default(parameter: ParameterDef) -> SelectionValue:
    """Default value implied by a parameter definition."""
    if isinstance(parameter, ChoiceParameter):
        return parameter.choices[0].id
    if isinstance(parameter, NumberParameter):
        return parameter.default
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def default_selection(parameters: Sequence[ParameterDef]) -> Selection:
    """Default selection implied by parameter definitions."""
    return {parameter.id: parameter_default(parameter) for parameter in parameters}


def validate_parameter_value(parameter: ParameterDef, value: object) -> SelectionValue:
    """Return a typed parameter value or raise ``ValueError``."""
    if isinstance(parameter, ChoiceParameter):
        choice = str(value)
        if choice not in {option.id for option in parameter.choices}:
            raise ValueError(f"{parameter.id}={choice!r} is not a valid choice")
        return choice
    if isinstance(parameter, NumberParameter):
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{parameter.id} must be numeric")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{parameter.id} must be finite")
        if not parameter.min <= number <= parameter.max:
            raise ValueError(f"{parameter.id}={number:g} is outside range")
        return value
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def canonical_selection_key(selection: Mapping[str, SelectionValue]) -> str:
    """Stable key for a projected source-local selection."""
    return json.dumps(dict(sorted(selection.items())), separators=(",", ":"), sort_keys=True)


def _view_source_ids(view: ViewDef) -> tuple[SourceId, ...]:
    """Source ids referenced by a view."""
    if isinstance(view, TableView | ChartView):
        return (view.source,)
    if isinstance(view, MapView | GraphViewSpec):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
