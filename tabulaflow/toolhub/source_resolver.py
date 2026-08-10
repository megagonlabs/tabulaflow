"""Runtime resolution of clean output sources to materialized results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from tabulaflow.core.outputs import (
    ChoiceParameter,
    ConstantResultPlan,
    NumberParameter,
    ParameterDef,
    ParameterId,
    QueryPlan,
    ResultId,
    ResultLookupPlan,
    ResultRecord,
    SelectionValue,
    SourceDef,
    canonical_selection_key,
)
from tabulaflow.toolhub.query_history import QueryHistory, TabularResult


class SourceResolutionError(ValueError):
    """A source cannot resolve for the requested selection."""


class ResultStore(Protocol):
    """Runtime store for materialized result metadata."""

    async def get_record(self, result_id: ResultId) -> ResultRecord:
        """Return metadata for a materialized result."""


class QueryHistoryResultStore:
    """ResultStore adapter over the current query history runtime."""

    def __init__(self, query_history: QueryHistory) -> None:
        self._query_history = query_history

    async def get_record(self, result_id: ResultId) -> ResultRecord:
        record = await self._query_history.get(result_id)
        row_count = None
        columns = None
        if isinstance(record.outcome, TabularResult):
            row_count = record.outcome.row_count
            columns = list(record.outcome.columns)
        return ResultRecord(
            id=record.record_id,
            db_alias=record.db_alias,
            query=record.query,
            connector_type=record.connector_type,
            parameter_values=record.parameter_values,
            row_count=row_count,
            columns=columns,
        )


class SourceResolver:
    """Resolve a SourceDef under a selection to an existing materialized result."""

    def __init__(self, result_store: ResultStore) -> None:
        self._result_store = result_store

    async def resolve(
        self,
        source: SourceDef,
        *,
        parameters: Mapping[ParameterId, ParameterDef],
        selection: Mapping[ParameterId, object],
    ) -> ResultRecord:
        plan = source.plan
        if isinstance(plan, ConstantResultPlan):
            return await self._result_store.get_record(plan.result_id)
        if isinstance(plan, ResultLookupPlan):
            key = canonical_selection_key(_project_selection(source, parameters, selection))
            for variant in plan.variants:
                if canonical_selection_key(variant.selection) == key:
                    return await self._result_store.get_record(variant.result_id)
            raise SourceResolutionError(f"source {source.id!r} has no result for selection {key}")
        if isinstance(plan, QueryPlan):
            raise SourceResolutionError("query source materialization is not implemented")
        raise TypeError(f"unsupported source plan {type(plan).__name__}")


def _project_selection(
    source: SourceDef,
    parameters: Mapping[ParameterId, ParameterDef],
    selection: Mapping[ParameterId, object],
) -> dict[ParameterId, SelectionValue]:
    projected: dict[ParameterId, SelectionValue] = {}
    for parameter_id in source.parameter_ids:
        parameter = parameters.get(parameter_id)
        if parameter is None:
            raise SourceResolutionError(f"source {source.id!r} references unknown parameter {parameter_id!r}")
        if parameter_id not in selection:
            raise SourceResolutionError(f"missing selection for {parameter_id!r}")
        projected[parameter_id] = _validate_parameter_value(parameter, selection[parameter_id])
    return projected


def _validate_parameter_value(parameter: ParameterDef, value: object) -> SelectionValue:
    if isinstance(parameter, ChoiceParameter):
        choice = str(value)
        if choice not in {option.id for option in parameter.choices}:
            raise SourceResolutionError(f"{parameter.id}={choice!r} is not a valid choice")
        return choice
    if isinstance(parameter, NumberParameter):
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise SourceResolutionError(f"{parameter.id} must be numeric")
        number = float(value)
        if not parameter.min <= number <= parameter.max:
            raise SourceResolutionError(f"{parameter.id}={number:g} is outside range")
        return value
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")
