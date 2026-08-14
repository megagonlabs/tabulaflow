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

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class ChoiceParameter(BaseModel):
    """Finite output parameter."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["choice"] = "choice"
    id: ParameterId
    label: str
    choices: list[ChoiceOption] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_choice_ids(self) -> "ChoiceParameter":
        _require_unique([choice.id for choice in self.choices], "choice ids")
        return self


class NumberParameter(BaseModel):
    """Numeric output parameter, optionally rendered as a slider."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["number"] = "number"
    id: ParameterId
    label: str
    min: float
    max: float
    step: float
    default: float
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


ParameterSpec: TypeAlias = Annotated[ChoiceParameter | NumberParameter, Field(discriminator="kind")]


class FixedResultSource(BaseModel):
    """Source that always resolves to one materialized result."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["fixed"] = "fixed"
    id: SourceId
    result_id: ResultId


class ParameterizedSource(BaseModel):
    """Source that materializes/cache results under a source-local selection."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["parameterized"] = "parameterized"
    id: SourceId
    parameter_ids: list[ParameterId]
    db_alias: str
    query_template: str


SourceSpec: TypeAlias = Annotated[FixedResultSource | ParameterizedSource, Field(discriminator="kind")]


class ResultMetadata(BaseModel):
    """Metadata for a concrete materialized result; data lives in runtime storage."""

    model_config = ConfigDict(extra="forbid")

    id: ResultId
    db_alias: str
    query: str
    connector_type: Literal["sql", "property_graph"] = "sql"
    source_selection: Selection = Field(default_factory=dict)
    row_count: int | None = None
    columns: list[str] | None = None
    affected_rows: int | None = None
    latency_seconds: float | None = None


class TableArtifactSpec(BaseModel):
    """Table artifact over one source."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["table"] = "table"
    id: ArtifactId
    label: str | None = None
    source_id: SourceId


class ChartArtifactSpec(BaseModel):
    """Chart artifact over one source."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["chart"] = "chart"
    id: ArtifactId
    label: str | None = None
    source_id: SourceId
    spec: dict[str, Any]


class MapArtifactSpec(BaseModel):
    """Map artifact over one or more sources."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["map"] = "map"
    id: ArtifactId
    label: str | None = None
    source_ids: list[SourceId]
    spec: dict[str, Any]


class GraphArtifactSpec(BaseModel):
    """Graph artifact over one or more sources."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["graph"] = "graph"
    id: ArtifactId
    label: str | None = None
    source_ids: list[SourceId]
    spec: dict[str, Any]


ArtifactSpec: TypeAlias = Annotated[
    TableArtifactSpec | ChartArtifactSpec | MapArtifactSpec | GraphArtifactSpec,
    Field(discriminator="kind"),
]


class OutputSpec(BaseModel):
    """Complete declarative contract for an interactive output."""

    model_config = ConfigDict(extra="forbid")

    parameters: list[ParameterSpec] = Field(default_factory=list)
    sources: list[SourceSpec] = Field(default_factory=list)
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
            for source_id in artifact_source_ids(artifact):
                if source_id not in known_sources:
                    raise ValueError(f"artifact {artifact.id!r} references unknown source {source_id!r}")
        return self


def _require_unique(values: Sequence[str], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must be unique")


def parameter_default(parameter: ParameterSpec) -> SelectionValue:
    """Default value implied by a parameter definition."""
    if isinstance(parameter, ChoiceParameter):
        return parameter.choices[0].id
    if isinstance(parameter, NumberParameter):
        return validate_parameter_value(parameter, parameter.default)
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def default_selection(parameters: Sequence[ParameterSpec]) -> Selection:
    """Default selection implied by parameter definitions."""
    return {parameter.id: parameter_default(parameter) for parameter in parameters}


def validate_parameter_value(parameter: ParameterSpec, value: object) -> SelectionValue:
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
        steps = (number - parameter.min) / parameter.step
        if not math.isclose(steps, round(steps), rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"{parameter.id}={number:g} is not aligned to step")
        if parameter.min.is_integer() and parameter.max.is_integer() and parameter.step.is_integer():
            return int(round(number))
        return value
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def canonical_selection_key(selection: Mapping[str, SelectionValue]) -> str:
    """Stable key for a projected source-local selection."""
    return json.dumps(dict(sorted(selection.items())), separators=(",", ":"), sort_keys=True)


def artifact_source_ids(artifact: ArtifactSpec) -> tuple[SourceId, ...]:
    """Source ids referenced by an artifact."""
    if isinstance(artifact, TableArtifactSpec | ChartArtifactSpec):
        return (artifact.source_id,)
    if isinstance(artifact, MapArtifactSpec | GraphArtifactSpec):
        return tuple(artifact.source_ids)
    raise TypeError(f"unsupported artifact {type(artifact).__name__}")
