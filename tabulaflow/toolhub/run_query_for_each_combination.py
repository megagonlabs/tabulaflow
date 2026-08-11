"""Run one query template over the combinations of a set of dimension choices."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from itertools import product
import math
import re
from textwrap import dedent
from typing import Annotated, ClassVar, TypeAlias

import jinja2
import jinja2.meta
import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Tool, ToolReturn

from tabulaflow.core.config import tabulaflow_config
from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.outputs import ResultLookupPlan, SourceDef
from tabulaflow.core.types import ErrorInfo, PredQuery
from tabulaflow.core.utils import flatten_multiline, format_df
from tabulaflow.toolhub.base import ToolCallOutcome
from tabulaflow.toolhub.engines.sql import format_sqlalchemy_error_msg
from tabulaflow.toolhub.output_store import OutputStore

DEFAULT_MAX_COMBINATIONS = 50

_SAMPLE_ROWS = 5
_FIRST_ROW_COLUMNS = 4
_FIRST_ROW_CELL_CHARS = 40
_MAX_REPORTED_ERRORS = 5
_KEYS_PER_ERROR = 3
_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True)
_SQL_COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


class QueryDimension(BaseModel):
    id: str = Field(min_length=1, description="Dimension id. The query template must reference it as a Jinja variable.")
    choices: list[str] = Field(
        min_length=1, description="Choice ids for this dimension. The template must branch on these values."
    )


Dimensions: TypeAlias = Annotated[list[QueryDimension], Field(min_length=1)]


@dataclass(frozen=True)
class CombinationQueryRun:
    """Result of one run-query-for-each-combination invocation."""

    output: str
    source: SourceDef


def selection_key(selection: dict[str, str]) -> str:
    """Key one dimension selection into a result-lookup source variant."""
    return ";".join(f"{dim}={choice}" for dim, choice in sorted(selection.items()))


def _source_dimensions(source: SourceDef) -> dict[str, list[str]]:
    if not isinstance(source.plan, ResultLookupPlan):
        return {}
    dimensions: dict[str, list[str]] = {parameter_id: [] for parameter_id in source.parameter_ids}
    for variant in source.plan.variants:
        for parameter_id in source.parameter_ids:
            value = str(variant.selection.get(parameter_id))
            if value not in dimensions[parameter_id]:
                dimensions[parameter_id].append(value)
    return dimensions


def _record_ids_by_selection(source: SourceDef) -> dict[str, str]:
    if not isinstance(source.plan, ResultLookupPlan):
        return {}
    return {selection_key({k: str(v) for k, v in variant.selection.items()}): variant.result_id for variant in source.plan.variants}


def _normalize(query: str) -> str:
    """Strip SQL comments and collapse whitespace, so no-op branches compare equal."""
    return " ".join(_SQL_COMMENT_RE.sub(" ", query).split())


def _rows_label(pred_query: PredQuery) -> str:
    df = pred_query.exec_result.df if pred_query.exec_result is not None else None
    if df is None:
        return "no result set"
    return f"{len(df)} row{'' if len(df) == 1 else 's'}"


def _format_table(pred_query: PredQuery) -> str:
    df = pred_query.exec_result.df if pred_query.exec_result is not None else None
    if df is None or df.empty:
        return "(query executed successfully, but results are empty)"
    return format_df(df, max_visible_rows=_SAMPLE_ROWS)


def _format_cell(value: object) -> str:
    """Render one cell as ``format_df`` would: ``[NULL]`` for nulls, ``.8g`` floats, one line."""
    try:
        if pd.isna(value):
            return "[NULL]"
    except (ValueError, TypeError):
        pass  # container cells (list, dict, ndarray) make pd.isna non-scalar
    if isinstance(value, float):
        return f"{value:.8g}"
    text = flatten_multiline(str(value))
    if len(text) > _FIRST_ROW_CELL_CHARS:
        half = _FIRST_ROW_CELL_CHARS // 2
        return f"{text[:half]}...{text[-half:]}"
    return text


def _format_first_row(pred_query: PredQuery) -> str | None:
    """Render a result's first row as ``column=value`` pairs, or ``None`` when it has no rows."""
    df = pred_query.exec_result.df if pred_query.exec_result is not None else None
    if df is None or df.empty:
        return None
    row = df.iloc[0]
    shown = min(len(df.columns), _FIRST_ROW_COLUMNS)
    pairs = ", ".join(f"{df.columns[index]}={_format_cell(row.iloc[index])}" for index in range(shown))
    return f"{pairs}, …" if shown < len(df.columns) else pairs


def _result_fingerprint(pred_query: PredQuery) -> tuple[tuple[str, ...], bytes] | None:
    """Fingerprint of everything a result displays, or ``None`` when unavailable.

    Column headers, row values and row order all count, since each is something the
    user sees; the pandas index does not, since it is never rendered.

    Unhashable cell types (DuckDB ``LIST`` / ``STRUCT`` / ``MAP`` / ``BLOB``) yield
    ``None``: the fingerprint only drives a diagnostic note, so dropping it beats
    stringifying every row to keep it.
    """
    df = pred_query.exec_result.df if pred_query.exec_result is not None else None
    if df is None or df.empty:
        return None
    try:
        digest = pd.util.hash_pandas_object(df, index=False).values.tobytes()
    except TypeError:
        return None
    return tuple(str(column) for column in df.columns), digest


def _repetition_notes(by_selection: dict[str, PredQuery]) -> dict[str, str]:
    """Note, per combination, the earlier combination it repeats.

    ``same query as`` is a render that deduplicated. ``same result as`` is two
    readings whose queries differ but whose output does not — a choice the user can
    switch to with no visible effect, which comparing rendered queries cannot catch.
    """
    first_by_query: dict[str, str] = {}
    first_by_result: dict[tuple[tuple[str, ...], bytes], str] = {}
    notes: dict[str, str] = {}
    for key, pred_query in by_selection.items():
        if (earlier := first_by_query.get(pred_query.query)) is not None:
            notes[key] = f"same query as {earlier}"
            continue
        first_by_query[pred_query.query] = key
        fingerprint = _result_fingerprint(pred_query)
        if fingerprint is None:
            continue
        if (earlier := first_by_result.get(fingerprint)) is not None:
            notes[key] = f"same result as {earlier}"
        else:
            first_by_result[fingerprint] = key
    return notes


def _format_run(source: SourceDef, by_selection: dict[str, PredQuery]) -> str:
    """Render the family header, the first combination in full, then the rest as row counts.

    The combination shown in full is the first choice of every dimension — the
    reading a panel opens on.
    """
    dimensions = _source_dimensions(source)
    record_ids_by_selection = _record_ids_by_selection(source)
    grid = " × ".join(f"{name} ({len(choices)})" for name, choices in dimensions.items())
    executed = len(set(record_ids_by_selection.values()))
    total = len(by_selection)
    identical = f" ({total - executed} identical)" if total > executed else ""
    header = f"{source.id} — dimensions: {grid} = {total} combinations, {executed} executed{identical}"

    notes = _repetition_notes(by_selection)
    (sample_key, sample), *others = by_selection.items()
    lines = [header, "", f"{sample_key} ({_rows_label(sample)}):", _format_table(sample)]
    if others:
        lines += ["", "other combinations:"]
        for key, pred_query in others:
            # A repeat needs no first row: it is the same one already shown for the
            # combination the note points at.
            annotation = notes.get(key)
            if annotation is None and (first_row := _format_first_row(pred_query)) is not None:
                annotation = f"first row: {first_row}"
            suffix = f" — {annotation}" if annotation is not None else ""
            lines.append(f"  {key} ({_rows_label(pred_query)}){suffix}")
    return "\n".join(lines)


def _error_summary(error: ErrorInfo) -> str:
    """One-line form of a query error: the driver's own first line.

    The rest is the echoed SQL and hints, which the agent already has as its template.
    """
    if error.exc_type == "TimeoutError":
        return "timed out"
    return (format_sqlalchemy_error_msg(error.message).splitlines() or [error.exc_type])[0]


def _format_failures(failures: dict[str, list[str]], executed: int) -> str:
    """One line per distinct error, naming the combinations that hit it."""
    failed = sum(len(keys) for keys in failures.values())
    lines = [f"{failed} of {executed} queries failed; anything not listed ran fine"]
    for message, keys in list(failures.items())[:_MAX_REPORTED_ERRORS]:
        shown = ", ".join(keys[:_KEYS_PER_ERROR])
        extra = f" +{len(keys) - _KEYS_PER_ERROR} more" if len(keys) > _KEYS_PER_ERROR else ""
        lines.append(f"  {shown}{extra} — {message}")
    if len(failures) > _MAX_REPORTED_ERRORS:
        lines.append(f"  (and {len(failures) - _MAX_REPORTED_ERRORS} more distinct errors)")
    return "\n".join(lines)


def _validate_dimensions(dimensions: list[QueryDimension], max_combinations: int) -> None:
    """Raise ``ValueError`` for duplicate ids or choices, or an oversized grid.

    Duplicates would silently collapse selection keys rather than fail, which is
    why they are checked here instead of left to the caller.
    """
    ids = [dim.id for dim in dimensions]
    if len(set(ids)) != len(ids):
        raise ValueError("dimension ids must be unique")
    for dim in dimensions:
        if len(set(dim.choices)) != len(dim.choices):
            raise ValueError(f"dimension {dim.id!r} has duplicate choices")
    total = math.prod(len(dim.choices) for dim in dimensions)
    if total > max_combinations:
        raise ValueError(f"{total} combinations exceeds the cap of {max_combinations}")


def _compile_template(dimensions: list[QueryDimension], query_template: str) -> jinja2.Template:
    """Compile the template, requiring its variables to be exactly the dimension ids."""
    try:
        used = jinja2.meta.find_undeclared_variables(_JINJA_ENV.parse(query_template))
        template = _JINJA_ENV.from_string(query_template)
    except Exception as exc:
        raise ValueError(f"template compile failed: {type(exc).__name__}: {exc}") from None
    declared = {dim.id for dim in dimensions}
    problems = []
    if declared - used:
        problems.append(f"missing template variables for dimensions: {', '.join(sorted(declared - used))}")
    if used - declared:
        problems.append(f"template variables not declared as dimensions: {', '.join(sorted(used - declared))}")
    if problems:
        raise ValueError("; ".join(problems))
    return template


def _check_every_dimension_matters(dimensions: list[QueryDimension], renders: list[tuple[dict[str, str], str]]) -> None:
    """Raise ``ValueError`` for a dimension whose choices never change the rendered query.

    Such a dimension is a toggle the user can flip with no effect, which a variable
    check alone misses: a template can mention it in a comment or a no-op position.
    """
    for dim in dimensions:
        if len(dim.choices) < 2:
            continue
        by_others: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
        for selection, query in renders:
            others = tuple(choice for name, choice in sorted(selection.items()) if name != dim.id)
            by_others[others].add(_normalize(query))
        if all(len(queries) == 1 for queries in by_others.values()):
            raise ValueError(f"changing dimension {dim.id!r} never changes the rendered query")


def _render_queries(dimensions: list[QueryDimension], query_template: str, max_combinations: int) -> dict[str, str]:
    """Validate the request and render one query per combination, keyed by selection."""
    _validate_dimensions(dimensions, max_combinations)
    query_template = dedent(query_template).strip()
    template = _compile_template(dimensions, query_template)
    names = [dim.id for dim in dimensions]
    renders: list[tuple[dict[str, str], str]] = []
    for choices in product(*(dim.choices for dim in dimensions)):
        selection = dict(zip(names, choices, strict=True))
        try:
            rendered = template.render(**selection).strip()
        except Exception as exc:
            key = selection_key(selection)
            raise ValueError(f"template render failed at {key}: {type(exc).__name__}: {exc}") from None
        renders.append((selection, rendered))
    _check_every_dimension_matters(dimensions, renders)
    return {selection_key(selection): query for selection, query in renders}


class RunQueryForEachCombinationTool:
    """Run one query template over the combinations of a set of dimension choices.

    Renders the template once per combination, executes the distinct renders
    concurrently against a registered database, and registers the whole set as one
    result-lookup source (``S*``) in ``OutputStore``.

    Attributes:
        registry: Registry the ``db_alias`` argument resolves against.
        timeout: Per-query timeout in seconds.
        max_combinations: Largest grid accepted; bigger requests are rejected.
    """

    name: ClassVar = "run_query_for_each_combination"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        output_store: OutputStore,
        timeout: int | None = None,
        max_combinations: int = DEFAULT_MAX_COMBINATIONS,
    ) -> None:
        self.registry = registry
        self.timeout = tabulaflow_config.query_timeout if timeout is None else timeout
        self.max_combinations = max_combinations
        self._output_store = output_store

    async def __call__(self, db_alias: str, dimensions: Dimensions, query_template: str) -> ToolReturn:
        """Render a query template once per combination of dimension choices and run each.

        Each dimension id is bound to the chosen choice id in the Jinja context, so the
        template branches on it and owns all query logic. Jinja block whitespace is
        trimmed so block-only ``if`` / ``elif`` / ``endif`` lines do not leave large
        blank gaps in the rendered SQL. The template must reference exactly the
        declared dimension ids, and every dimension must change the rendered query.
        Combinations that render identically are executed once. The whole set is
        recorded as one result-lookup source (``S*``).

        Example:
        ```python
        run_query_for_each_combination(
            db_alias="workspace",
            dimensions=[
                {"id": "ranking", "choices": ["net_revenue", "order_count"]},
                {"id": "period", "choices": ["completed_qtr", "last_90_days"]},
            ],
            query_template='''
            SELECT customer_name AS customer,
              {% if ranking == "net_revenue" %} SUM(net_revenue_usd) AS value
              {% elif ranking == "order_count" %} COUNT(*) AS value
              {% endif %}
            FROM orders
            WHERE {% if period == "completed_qtr" %} order_date >= DATE '2026-04-01' AND order_date < DATE '2026-07-01'
                  {% elif period == "last_90_days" %} order_date > CURRENT_DATE - INTERVAL 90 DAY
                  {% endif %}
            GROUP BY customer_name ORDER BY value DESC LIMIT 5
            ''',
        )
        ```

        Args:
            db_alias: Alias of the target database.
            dimensions: Dimensions to vary over. Choice ids are the values supplied to
                the Jinja variables.
            query_template: Jinja template rendered and executed for each combination.
        """
        try:
            run = await self.execute(db_alias, dimensions, query_template)
        except ValueError as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(
            return_value=run.output,
            metadata=ToolCallOutcome(count=len(_record_ids_by_selection(run.source)), unit="combinations"),
        )

    async def execute(self, db_alias: str, dimensions: Dimensions, query_template: str) -> CombinationQueryRun:
        """Run the template over every combination and register the resulting source.

        Raises:
            ValueError: If the alias is unknown, the request is invalid, or a
                combination's query fails — in which case nothing is registered.
        """
        connector = self._connector(db_alias)
        queries = _render_queries(dimensions, query_template, self.max_combinations)

        # Distinct renders only, in combination order; the connector's own semaphores
        # bound how many of them actually run at once.
        distinct: dict[str, tuple[str, str]] = {}
        for selection_key, query in queries.items():
            distinct.setdefault(_normalize(query), (selection_key, query))
        exec_results = await asyncio.gather(
            *(connector.run_query_async(query, timeout=self.timeout) for _, query in distinct.values())
        )

        pred_queries: dict[str, PredQuery] = {}
        failures: dict[str, list[str]] = {}
        for (normalized, (selection_key, query)), exec_result in zip(distinct.items(), exec_results, strict=True):
            if (error := exec_result.error) is not None:
                failures.setdefault(_error_summary(error), []).append(selection_key)
                continue
            pred_queries[normalized] = PredQuery(query=query, exec_result=exec_result)
        if failures:
            raise ValueError(_format_failures(failures, len(distinct)))

        by_selection = {key: pred_queries[_normalize(query)] for key, query in queries.items()}
        source = await self._output_store.add_lookup_source(
            db_alias,
            connector.connector_type,
            {dim.id: list(dim.choices) for dim in dimensions},
            by_selection,
        )
        return CombinationQueryRun(output=_format_run(source, by_selection), source=source)

    def _connector(self, db_alias: str) -> NL2QDBConnector:
        try:
            return self.registry.get(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown db_alias: {db_alias!r}; available: {available}") from None

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
