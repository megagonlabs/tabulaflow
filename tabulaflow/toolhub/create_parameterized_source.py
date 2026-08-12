"""Create declarative parameterized output sources."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import ClassVar

import jinja2
import jinja2.meta
from pydantic_ai import Tool, ToolReturn

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.outputs import (
    ChoiceParameter,
    NumberParameter,
    ParameterDef,
    ParameterizedSource,
    SelectionValue,
)
from tabulaflow.toolhub.base import ToolCallOutcome
from tabulaflow.toolhub.output_store import OutputStore, render_parameterized_query
from tabulaflow.toolhub.run_query import RunQueryTool

_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True)


@dataclass(frozen=True)
class CreatedParameterizedSource:
    output: str
    source: ParameterizedSource


class CreateParameterizedSourceTool:
    """Create a source whose query is controlled by declared output parameters."""

    name: ClassVar = "create_parameterized_source"

    def __init__(
        self,
        registry: DBRegistry,
        output_store: OutputStore,
        *,
        default_max_warm_variants: int = 10,
    ) -> None:
        self._registry = registry
        self._output_store = output_store
        self._default_max_warm_variants = default_max_warm_variants

    async def __call__(
        self,
        db_alias: str,
        parameters: list[ParameterDef],
        query_template: str,
        max_warm_variants: int | None = None,
    ) -> ToolReturn:
        """Create a parameterized source and warm its default or small finite choice grid.

        Example:
        ```python
        create_parameterized_source(
            db_alias="workspace",
            parameters=[
                {
                    "kind": "choice",
                    "id": "metric",
                    "label": "Ranking metric",
                    "choices": [
                        {"id": "revenue", "label": "Revenue"},
                        {"id": "profit", "label": "Profit"},
                        {"id": "orders", "label": "Order count"},
                    ],
                },
                {
                    "kind": "number",
                    "id": "min_spend",
                    "label": "Minimum spend",
                    "min": 0,
                    "max": 100000,
                    "step": 5000,
                    "default": 10000,
                    "unit": "USD",
                },
            ],
            query_template='''
                SELECT customer,
                {% if metric == "revenue" %} SUM(revenue_usd) AS value
                {% elif metric == "profit" %} SUM(profit_usd) AS value
                {% elif metric == "orders" %} COUNT(*) AS value
                {% endif %}
                FROM orders
                GROUP BY customer
                HAVING SUM(revenue_usd) >= {{ min_spend }}
                ORDER BY value DESC
            ''',
        )
        ```

        Args:
            db_alias: Alias of the target database.
            parameters: Choice or number parameters referenced by the Jinja query template.
            query_template: Jinja template rendered with validated parameter values.
            max_warm_variants: Maximum finite choice combinations to precompute. If omitted,
                the session default is used. Numeric parameters warm only the default selection.
        """
        try:
            created = await self.execute(db_alias, parameters, query_template, max_warm_variants)
        except ValueError as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(return_value=created.output, metadata=ToolCallOutcome(count=1, unit="source"))

    async def execute(
        self,
        db_alias: str,
        parameters: list[ParameterDef],
        query_template: str,
        max_warm_variants: int | None = None,
    ) -> CreatedParameterizedSource:
        if max_warm_variants is None:
            max_warm_variants = self._default_max_warm_variants
        if max_warm_variants < 1:
            raise ValueError("max_warm_variants must be >= 1")
        try:
            connector = self._registry.get(db_alias)
        except ValueError:
            available = ", ".join(self._registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown db_alias: {db_alias!r}; available: {available}") from None
        _validate_parameters(parameters)
        _validate_template(parameters, query_template)
        source = await self._output_store.add_parameterized_source(db_alias, parameters, query_template)
        selections = _warm_selections(parameters, max_warm_variants)
        runner = RunQueryTool(connector)
        lines = [f"[source_id={source.id}]", f"created parameterized source {source.id}"]
        for index, selection in enumerate(selections):
            query = render_parameterized_query(query_template, selection)
            execution = await runner.execute(query)
            pred_query = execution.pred_query
            if pred_query.exec_result is not None and pred_query.exec_result.error is not None:
                raise ValueError(f"warm query failed for {_selection_label(selection)}: {pred_query.exec_result.error.message}")
            pred_query.parameter_values = dict(selection)
            result_id = await self._output_store.add_cached_parameterized_result(
                source,
                connector.connector_type,
                selection,
                pred_query,
            )
            if index == 0:
                lines += [f"default {_selection_label(selection)} -> {result_id}:", execution.output]
            else:
                lines.append(f"warmed {_selection_label(selection)} -> {result_id}")
        if len(selections) == 1:
            lines.append("other selections will materialize lazily when selected")
        return CreatedParameterizedSource(output="\n".join(lines), source=source)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)


def _validate_parameters(parameters: list[ParameterDef]) -> None:
    if not parameters:
        raise ValueError("parameters must not be empty")
    ids = [parameter.id for parameter in parameters]
    if len(set(ids)) != len(ids):
        raise ValueError("parameter ids must be unique")
    for parameter in parameters:
        if isinstance(parameter, NumberParameter):
            for field_name, value in (("min", parameter.min), ("max", parameter.max), ("step", parameter.step), ("default", parameter.default)):
                if not math.isfinite(value):
                    raise ValueError(f"number parameter {parameter.id!r} {field_name} must be finite")


def _validate_template(parameters: list[ParameterDef], query_template: str) -> None:
    try:
        parsed = _JINJA_ENV.parse(query_template)
    except jinja2.TemplateError as exc:
        raise ValueError(f"invalid query_template: {exc}") from None
    used = jinja2.meta.find_undeclared_variables(parsed)
    declared = {parameter.id for parameter in parameters}
    problems: list[str] = []
    if missing := sorted(declared - used):
        problems.append(f"missing template variables for parameters: {', '.join(missing)}")
    if extra := sorted(used - declared):
        problems.append(f"template variables not declared as parameters: {', '.join(extra)}")
    if problems:
        raise ValueError("; ".join(problems))


def _warm_selections(parameters: list[ParameterDef], max_warm_variants: int) -> list[dict[str, SelectionValue]]:
    default = _default_selection(parameters)
    if any(isinstance(parameter, NumberParameter) for parameter in parameters):
        return [default]
    choice_parameters = [parameter for parameter in parameters if isinstance(parameter, ChoiceParameter)]
    combinations = math.prod(len(parameter.choices) for parameter in choice_parameters)
    if combinations > max_warm_variants:
        return [default]
    selections: list[dict[str, SelectionValue]] = []
    for choices in itertools.product(*(parameter.choices for parameter in choice_parameters)):
        selections.append({parameter.id: choice.id for parameter, choice in zip(choice_parameters, choices, strict=True)})
    return selections or [default]


def _default_selection(parameters: list[ParameterDef]) -> dict[str, SelectionValue]:
    out: dict[str, SelectionValue] = {}
    for parameter in parameters:
        if isinstance(parameter, ChoiceParameter):
            out[parameter.id] = parameter.default if parameter.default is not None else parameter.choices[0].id
        elif isinstance(parameter, NumberParameter):
            out[parameter.id] = parameter.default
    return out


def _selection_label(selection: dict[str, SelectionValue]) -> str:
    return ";".join(f"{key}={value}" for key, value in sorted(selection.items())) or "default"
