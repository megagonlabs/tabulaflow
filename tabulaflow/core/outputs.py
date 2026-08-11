"""Pure output specification models.

These models describe an interactive output without executing anything. Runtime
state such as source caches, query records, connector access, and materialized
DataFrames belongs outside ``core``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator


SelectionValue: TypeAlias = str | int | float | bool
ParameterId: TypeAlias = str
SourceId: TypeAlias = str
ArtifactId: TypeAlias = str
ResultId: TypeAlias = str
SelectionKey: TypeAlias = str


class ChoiceOption(BaseModel):
    """One finite parameter option."""

    id: str
    label: str


class ChoiceParameter(BaseModel):
    """Finite answer parameter."""

    kind: Literal["choice"] = "choice"
    id: ParameterId
    label: str
    choices: list[ChoiceOption] = Field(min_length=1)
    default: str | None = None

    @model_validator(mode="after")
    def validate_default(self) -> "ChoiceParameter":
        if self.default is not None and self.default not in {choice.id for choice in self.choices}:
            raise ValueError("choice parameter default must be one of choices")
        return self


class NumberParameter(BaseModel):
    """Numeric answer parameter, optionally rendered as a slider."""

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


class ConstantResultPlan(BaseModel):
    """Plan that always returns one already-materialized result."""

    kind: Literal["constant_result"] = "constant_result"
    result_id: ResultId


class ResultVariant(BaseModel):
    """One precomputed result for a source-local selection."""

    selection: dict[ParameterId, SelectionValue]
    result_id: ResultId


class ResultLookupPlan(BaseModel):
    """Plan that maps source-local selections to existing results."""

    kind: Literal["result_lookup"] = "result_lookup"
    variants: list[ResultVariant]


class QueryPlan(BaseModel):
    """Plan that can produce a result by executing a parameterized query."""

    kind: Literal["query"] = "query"
    db_alias: str
    query_template: str
    connector_type: Literal["sql", "property_graph"] = "sql"


SourcePlan = Annotated[ConstantResultPlan | ResultLookupPlan | QueryPlan, Field(discriminator="kind")]


class ResultRecord(BaseModel):
    """Metadata for a concrete materialized query result; data lives in runtime storage."""

    id: ResultId
    db_alias: str
    query: str
    connector_type: Literal["sql", "property_graph"] = "sql"
    parameter_values: dict[ParameterId, SelectionValue] = Field(default_factory=dict)
    row_count: int | None = None
    columns: list[str] | None = None


class SourceDef(BaseModel):
    """Declarative, selection-dependent provider of concrete results."""

    id: SourceId
    parameter_ids: list[ParameterId] = Field(default_factory=list)
    plan: SourcePlan


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


class GraphArtifactView(BaseModel):
    """Graph view over one or more sources."""

    kind: Literal["graph"] = "graph"
    sources: list[SourceId]
    spec: dict[str, Any]


ViewDef = Annotated[TableView | ChartView | MapView | GraphArtifactView, Field(discriminator="kind")]


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
    default_selection: dict[ParameterId, SelectionValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_spec(self) -> "OutputSpec":
        parameter_ids = [parameter.id for parameter in self.parameters]
        source_ids = [source.id for source in self.sources]
        artifact_ids = [artifact.id for artifact in self.artifacts]
        _require_unique(parameter_ids, "parameter ids")
        _require_unique(source_ids, "source ids")
        _require_unique(artifact_ids, "artifact ids")

        defaults = _parameter_defaults(self.parameters)
        defaults.update(self.default_selection)
        self.default_selection = defaults
        parameter_by_id = {parameter.id: parameter for parameter in self.parameters}
        for key, value in self.default_selection.items():
            parameter = parameter_by_id.get(key)
            if parameter is None:
                raise ValueError(f"default selection references unknown parameter {key!r}")
            _validate_parameter_value(parameter, value)

        for source in self.sources:
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


def _parameter_defaults(parameters: Sequence[ParameterDef]) -> dict[ParameterId, SelectionValue]:
    """Default selection implied by parameter definitions."""
    defaults: dict[ParameterId, SelectionValue] = {}
    for parameter in parameters:
        if isinstance(parameter, ChoiceParameter):
            defaults[parameter.id] = parameter.default if parameter.default is not None else parameter.choices[0].id
        elif isinstance(parameter, NumberParameter):
            defaults[parameter.id] = parameter.default
    return defaults


def _validate_parameter_value(parameter: ParameterDef, value: object) -> SelectionValue:
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
    if isinstance(view, MapView | GraphArtifactView):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
