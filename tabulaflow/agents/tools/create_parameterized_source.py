"""Create declarative parameterized artifact sources."""

from __future__ import annotations

import itertools
import math
import asyncio
from dataclasses import dataclass
from typing import ClassVar

import jinja2
import jinja2.meta
import pandas as pd
from pydantic_ai import Tool, ToolReturn

from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.output.specs import (
    ChoiceParameter,
    NumberParameter,
    ParameterSpec,
    ParameterizedArtifactSource,
    Selection,
    default_selection,
)
from tabulaflow.core.results import ErrorInfo, ExecResult
from tabulaflow.output.formatting import format_dataframe, format_single_line_text
from tabulaflow.agents.tools.protocols import ToolCallOutcome
from tabulaflow.agents.tools._sql import format_sqlalchemy_error_msg
from tabulaflow.output.store import OutputStore, ArtifactSourceNotApplicable, render_parameterized_query

_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True)
_JINJA_ENV.globals["not_applicable"] = lambda reason="not applicable": None
# Failure reports group by distinct error. Limit how many error groups and
# failing selection labels per group are printed so large warm grids stay readable.
_MAX_REPORTED_ERRORS = 5
_KEYS_PER_ERROR = 3
_FIRST_ROW_COLUMNS = 4
_FIRST_ROW_CELL_CHARS = 40
_UNSET = object()


@dataclass(frozen=True)
class CreatedParameterizedArtifactSource:
    """Created artifact-source metadata returned by programmatic execution."""

    output: str
    artifact_source: ParameterizedArtifactSource


class CreateParameterizedArtifactSourceTool:
    """Create an artifact source whose query is controlled by output parameters."""

    name: ClassVar = "create_parameterized_source"

    def __init__(
        self,
        registry: DataConnectorRegistry,
        output_store: OutputStore,
        *,
        timeout: int | None | object = _UNSET,
        default_max_warm_variants: int = 10,
    ) -> None:
        self._registry = registry
        self._output_store = output_store
        self.timeout = timeout
        self._default_max_warm_variants = default_max_warm_variants

    async def __call__(
        self,
        connector_alias: str,
        parameters: list[ParameterSpec],
        query_template: str,
        max_warm_variants: int | None = None,
    ) -> ToolReturn:
        """Create a parameterized source and warm its default or small finite choice grid.

        Example:
        ```python
        create_parameterized_source(
            connector_alias="workspace",
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

        Use ``not_applicable(reason)`` when a source intentionally does not apply
        for a parameter branch; no SQL is run for that selection, and dependent
        artifacts render the reason as a not-applicable message.

        Example:
        ```python
        create_parameterized_source(
            connector_alias="workspace",
            parameters=[
                {
                    "kind": "choice",
                    "id": "metric",
                    "label": "Metric",
                    "choices": [
                        {"id": "revenue", "label": "Revenue"},
                        {"id": "orders", "label": "Orders"},
                    ],
                },
            ],
            query_template='''
                {% if metric != "revenue" %}
                  {{ not_applicable("Revenue detail only applies when metric is Revenue") }}
                {% endif %}

                SELECT customer, revenue_usd
                FROM customer_revenue
                ORDER BY revenue_usd DESC
            ''',
        )
        ```

        Args:
            connector_alias: Alias of the connector that executes rendered queries.
            parameters: Choice or number parameters referenced by the Jinja query template.
                For choice parameters, the first choice is the default.
            query_template: Jinja template rendered with validated parameter values.
                It may call ``not_applicable(reason)`` to declare that the source
                intentionally does not apply for the active selection.
            max_warm_variants: Maximum finite choice combinations to precompute. If omitted,
                the session default is used. Numeric parameters are fixed at their
                defaults while choice combinations are warmed up to this cap.
        """
        try:
            created = await self.execute(connector_alias, parameters, query_template, max_warm_variants)
        except ValueError as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(return_value=created.output, metadata=ToolCallOutcome(count=1, unit="source"))

    async def execute(
        self,
        connector_alias: str,
        parameters: list[ParameterSpec],
        query_template: str,
        max_warm_variants: int | None = None,
    ) -> CreatedParameterizedArtifactSource:
        """Validate, create, and warm a parameterized result source.

        Args:
            connector_alias: Alias of the connector that executes rendered queries.
            parameters: Parameters referenced by ``query_template``.
            query_template: Jinja query template rendered for each warmed selection.
            max_warm_variants: Maximum finite choice combinations to precompute.

        Returns:
            The created source and a model-facing summary of its warmed results.

        Raises:
            ValueError: If configuration is invalid or a warmed query fails.
        """

        if max_warm_variants is None:
            max_warm_variants = self._default_max_warm_variants
        if max_warm_variants < 1:
            raise ValueError("max_warm_variants must be >= 1")
        try:
            connector = self._registry.get(connector_alias)
        except ValueError:
            available = ", ".join(self._registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown connector_alias: {connector_alias!r}; available: {available}") from None
        _validate_parameters(parameters)
        _validate_template(parameters, query_template)
        warm_queries: list[tuple[Selection, str]] = []
        not_applicable_count = 0
        for selection in _warm_selections(parameters, max_warm_variants):
            try:
                warm_queries.append((selection, render_parameterized_query(query_template, selection)))
            except ArtifactSourceNotApplicable:
                not_applicable_count += 1
        if not warm_queries:
            raise ValueError("all warmed selections were not applicable; source was not created")
        if self.timeout is _UNSET:
            exec_results = await asyncio.gather(*(connector.run_query_async(query) for _, query in warm_queries))
        else:
            exec_results = await asyncio.gather(
                *(
                    connector.run_query_async(query, timeout=self.timeout)  # type: ignore[arg-type]
                    for _, query in warm_queries
                )
            )
        executions: list[tuple[Selection, str, ExecResult]] = []
        failures: dict[str, list[str]] = {}
        for (selection, query), exec_result in zip(warm_queries, exec_results, strict=True):
            label = _selection_label(selection)
            if (error := exec_result.error) is not None:
                failures.setdefault(_error_summary(error), []).append(label)
                continue
            executions.append((selection, query, exec_result))
        if failures:
            raise ValueError(_format_failures(failures, len(warm_queries)))

        source = self._output_store.add_parameterized_artifact_source(connector_alias, parameters, query_template)
        lines = [f"[source_id={source.id}]", f"created parameterized source {source.id}"]
        for selection, query, exec_result in executions:
            await self._output_store.cache_parameterized_result(
                source.id, connector.language, selection, query, exec_result
            )
        first_selection, _, first_exec_result = executions[0]
        default_label = _selection_label(default_selection(parameters))
        first_label = _selection_label(first_selection)
        heading = "default" if first_label == default_label else "first applicable warmed selection"
        lines += [f"{heading} {first_label}:", _format_exec_result(first_exec_result)]
        other_lines: list[str] = []
        for selection, _, exec_result in executions[1:]:
            other_lines.append(_format_other_warmed_selection(selection, exec_result))
        if not_applicable_count:
            label = "selection" if not_applicable_count == 1 else "selections"
            other_lines.append(f"  {not_applicable_count} warmed {label} not applicable")
        if other_lines:
            lines += ["", "other warmed selections:", *other_lines]
        if len(warm_queries) == 1:
            lines.append("other selections will materialize lazily when selected")
        return CreatedParameterizedArtifactSource(output="\n".join(lines), artifact_source=source)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)


def _validate_parameters(parameters: list[ParameterSpec]) -> None:
    if not parameters:
        raise ValueError("parameters must not be empty")
    ids = [parameter.id for parameter in parameters]
    if len(set(ids)) != len(ids):
        raise ValueError("parameter ids must be unique")
    for parameter in parameters:
        if isinstance(parameter, NumberParameter):
            for field_name, value in (
                ("min", parameter.min),
                ("max", parameter.max),
                ("step", parameter.step),
                ("default", parameter.default),
            ):
                if not math.isfinite(value):
                    raise ValueError(f"number parameter {parameter.id!r} {field_name} must be finite")


def _validate_template(parameters: list[ParameterSpec], query_template: str) -> None:
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


def _warm_selections(parameters: list[ParameterSpec], max_warm_variants: int) -> list[Selection]:
    default = default_selection(parameters)
    choice_parameters = [parameter for parameter in parameters if isinstance(parameter, ChoiceParameter)]
    if not choice_parameters:
        return [default]
    combinations = math.prod(len(parameter.choices) for parameter in choice_parameters)
    if combinations > max_warm_variants:
        return [default]
    selections: list[Selection] = []
    for choices in itertools.product(*(parameter.choices for parameter in choice_parameters)):
        selection = dict(default)
        selection.update(
            {parameter.id: choice.id for parameter, choice in zip(choice_parameters, choices, strict=True)}
        )
        selections.append(selection)
    return selections or [default]


def _selection_label(selection: Selection) -> str:
    return ";".join(f"{key}={value}" for key, value in sorted(selection.items())) or "default"


def _format_exec_result(exec_result: ExecResult) -> str:
    if exec_result.df is None:
        affected = exec_result.affected_rows
        if affected is None:
            return "(statement executed successfully)"
        return f"(statement executed successfully, {affected} row{'s' if affected != 1 else ''} affected)"
    if exec_result.df.empty:
        return "(query executed successfully, but results are empty)"
    return f"{format_dataframe(exec_result.df)}\n({len(exec_result.df)} row{'' if len(exec_result.df) == 1 else 's'})"


def _format_other_warmed_selection(selection: Selection, exec_result: ExecResult) -> str:
    first_row = _format_first_row(exec_result)
    suffix = f" — first row: {first_row}" if first_row is not None else ""
    return f"  {_selection_label(selection)} ({_rows_label(exec_result)}){suffix}"


def _rows_label(exec_result: ExecResult) -> str:
    if exec_result.df is None:
        return "no result set"
    if exec_result.df.empty:
        return "empty"
    return f"{len(exec_result.df)} row{'' if len(exec_result.df) == 1 else 's'}"


def _format_first_row(exec_result: ExecResult) -> str | None:
    df = exec_result.df
    if df is None or df.empty:
        return None
    row = df.iloc[0]
    shown = min(len(df.columns), _FIRST_ROW_COLUMNS)
    pairs = ", ".join(f"{df.columns[index]}={_format_cell(row.iloc[index])}" for index in range(shown))
    return f"{pairs}, …" if shown < len(df.columns) else pairs


def _format_cell(value: object) -> str:
    try:
        if pd.isna(value):
            return "[NULL]"
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        return f"{value:.8g}"
    text = format_single_line_text(str(value))
    if len(text) > _FIRST_ROW_CELL_CHARS:
        half = _FIRST_ROW_CELL_CHARS // 2
        return f"{text[:half]}...{text[-half:]}"
    return text


def _error_summary(error: ErrorInfo) -> str:
    if error.exc_type == "TimeoutError":
        return "timed out"
    return (format_sqlalchemy_error_msg(error.message).splitlines() or [error.exc_type])[0]


def _format_failures(failures: dict[str, list[str]], executed: int) -> str:
    failed = sum(len(keys) for keys in failures.values())
    lines = [f"{failed} of {executed} warm queries failed; source was not created"]
    for message, keys in list(failures.items())[:_MAX_REPORTED_ERRORS]:
        shown = ", ".join(keys[:_KEYS_PER_ERROR])
        extra = f" +{len(keys) - _KEYS_PER_ERROR} more" if len(keys) > _KEYS_PER_ERROR else ""
        lines.append(f"  {shown}{extra} — {message}")
    if len(failures) > _MAX_REPORTED_ERRORS:
        lines.append(f"  (and {len(failures) - _MAX_REPORTED_ERRORS} more distinct errors)")
    return "\n".join(lines)
