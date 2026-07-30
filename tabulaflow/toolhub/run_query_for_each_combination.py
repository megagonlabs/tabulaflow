"""Run a query template over a cartesian product of dimension choices."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from itertools import product
import re
from typing import ClassVar

import jinja2
import jinja2.meta
from pydantic import BaseModel, Field

from tabulaflow.core.config import tabulaflow_config
from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.core.types import PredQuery
from tabulaflow.core.utils import format_df
from tabulaflow.toolhub.query_history import QueryFamily

_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)
DEFAULT_MAX_COMBINATIONS = 100
_LINE_COMMENT_RE = re.compile(r"--.*?(?=\n|$)")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


class QueryDimension(BaseModel):
    id: str = Field(description="Dimension id. The query template must reference it as a Jinja variable.")
    choices: list[str] = Field(description="Choice ids for this dimension. The template must branch on these values.")


@dataclass(frozen=True)
class CombinationQueryRun:
    """Result of running one query template across dimension selections."""

    dimensions: dict[str, list[str]]
    query_template: str
    pred_queries_by_selection: dict[str, PredQuery]
    executed_count: int


def _selection_key(selection: dict[str, str]) -> str:
    return ";".join(f"{dim}={selection[dim]}" for dim in sorted(selection))


def _format_dimensions(dimensions: list[QueryDimension]) -> str:
    return " × ".join(f"{dim.id} ({len(dim.choices)})" for dim in dimensions)


def _semantic_sql(sql: str) -> str:
    sql = _BLOCK_COMMENT_RE.sub("", sql)
    sql = _LINE_COMMENT_RE.sub("", sql)
    return " ".join(sql.split())


def _combinations(dimensions: list[QueryDimension]) -> list[dict[str, str]]:
    return [
        dict(zip((dim.id for dim in dimensions), choices, strict=True))
        for choices in product(*(d.choices for d in dimensions))
    ]


class RunQueryForEachCombinationTool:
    """Run one Jinja query template over combinations on a single connector."""

    name: ClassVar = "run_query_for_each_combination"

    def __init__(
        self,
        db_connector: NL2QDBConnector,
        *,
        timeout: int | None = None,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        max_combinations: int = DEFAULT_MAX_COMBINATIONS,
    ) -> None:
        self.db_connector = db_connector
        self.timeout = tabulaflow_config.query_timeout if timeout is None else timeout
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self.max_combinations = max_combinations

    async def execute(
        self,
        dimensions: list[QueryDimension],
        query_template: str,
    ) -> CombinationQueryRun:
        """Run a SQL Jinja template over every combination of dimension choices.

        Use this when one result card needs the same query shape evaluated across a
        small grid of interpretations. Each dimension id is available in the Jinja
        context as the selected choice id. The template must reference exactly the
        declared dimension ids, and each dimension must change the rendered SQL.
        Identical rendered SQL is executed once and shared across matching
        combinations.

        Args:
            dimensions: Dimensions to vary over. Choice ids are the values supplied
                to the Jinja variables.
            query_template: SQL Jinja template to render and execute for each
                dimension-choice combination.
        """

        validation_error = self._validate(dimensions, query_template)
        if validation_error is not None:
            raise ValueError(validation_error)

        selections = _combinations(dimensions)
        template = _JINJA_ENV.from_string(query_template)
        rendered_by_key: OrderedDict[str, str] = OrderedDict()
        rendered_items_by_selection: list[tuple[dict[str, str], str]] = []
        try:
            for selection in selections:
                rendered_query = template.render(**selection).strip()
                rendered_by_key[_selection_key(selection)] = rendered_query
                rendered_items_by_selection.append((selection, rendered_query))
        except jinja2.TemplateError as exc:
            raise ValueError(f"template render failed: {type(exc).__name__}: {exc}") from exc

        dimension_effect_error = self._validate_dimensions_affect_sql(dimensions, rendered_items_by_selection)
        if dimension_effect_error is not None:
            raise ValueError(dimension_effect_error)

        pred_by_sql: OrderedDict[str, PredQuery] = OrderedDict()
        errors: list[str] = []
        for selection_key, rendered_query in rendered_by_key.items():
            if rendered_query in pred_by_sql:
                continue
            exec_result = await self.db_connector.run_query_async(rendered_query, timeout=self.timeout)
            pred_query = PredQuery(query=rendered_query, exec_result=exec_result)
            if exec_result.error is not None:
                errors.append(f"{selection_key}: {exec_result.error.message}")
            pred_by_sql[rendered_query] = pred_query

        if errors:
            raise ValueError("query failed for " + "; ".join(errors[:5]))

        pred_queries_by_selection = {
            selection_key: pred_by_sql[rendered_query] for selection_key, rendered_query in rendered_by_key.items()
        }
        return CombinationQueryRun(
            dimensions={dim.id: list(dim.choices) for dim in dimensions},
            query_template=query_template,
            pred_queries_by_selection=pred_queries_by_selection,
            executed_count=len(pred_by_sql),
        )

    async def __call__(
        self,
        dimensions: list[QueryDimension],
        query_template: str,
    ) -> CombinationQueryRun:
        return await self.execute(dimensions, query_template)

    def _validate(self, dimensions: list[QueryDimension], query_template: str) -> str | None:
        if not dimensions:
            return "at least one dimension is required"
        dim_ids = [dim.id for dim in dimensions]
        if len(set(dim_ids)) != len(dim_ids):
            return "dimension ids must be unique"
        for dim in dimensions:
            if not dim.id.strip():
                return "dimension ids cannot be empty"
            if not dim.choices:
                return f"dimension {dim.id!r} must have at least one choice"
            if len(set(dim.choices)) != len(dim.choices):
                return f"dimension {dim.id!r} has duplicate choices"
            if any(not choice.strip() for choice in dim.choices):
                return f"dimension {dim.id!r} has an empty choice id"
        total = 1
        for dim in dimensions:
            total *= len(dim.choices)
        if total > self.max_combinations:
            return f"{total} combinations exceeds the cap of {self.max_combinations}"
        try:
            ast = _JINJA_ENV.parse(query_template)
        except jinja2.TemplateSyntaxError as exc:
            return f"template syntax error: {exc.message}"
        variables = jinja2.meta.find_undeclared_variables(ast)
        expected = set(dim_ids)
        if variables != expected:
            missing = sorted(expected - variables)
            extra = sorted(variables - expected)
            parts = []
            if missing:
                parts.append(f"missing template variables for dimensions: {', '.join(missing)}")
            if extra:
                parts.append(f"template variables not declared as dimensions: {', '.join(extra)}")
            return "; ".join(parts)
        return None

    def _validate_dimensions_affect_sql(
        self,
        dimensions: list[QueryDimension],
        rendered_items_by_selection: list[tuple[dict[str, str], str]],
    ) -> str | None:
        if len(dimensions) == 1:
            dim = dimensions[0]
            if len(dim.choices) > 1 and len({_semantic_sql(sql) for _, sql in rendered_items_by_selection}) == 1:
                return f"changing dimension {dim.id!r} never changes the rendered SQL"
            return None
        for dim in dimensions:
            if len(dim.choices) == 1:
                continue
            changes = False
            for i, (selection_i, sql_i) in enumerate(rendered_items_by_selection):
                for j in range(i + 1, len(rendered_items_by_selection)):
                    selection_j, sql_j = rendered_items_by_selection[j]
                    if selection_i[dim.id] == selection_j[dim.id]:
                        continue
                    if all(
                        selection_i[other.id] == selection_j[other.id] for other in dimensions if other.id != dim.id
                    ):
                        changes = changes or _semantic_sql(sql_i) != _semantic_sql(sql_j)
                if changes:
                    break
            if not changes:
                return f"changing dimension {dim.id!r} never changes the rendered SQL"
        return None

    def format_run_summary(
        self,
        family: QueryFamily,
        run: CombinationQueryRun,
    ) -> str:
        pred_queries_by_selection = run.pred_queries_by_selection
        total = len(pred_queries_by_selection)
        identical = total - run.executed_count
        line = (
            f"{family.family_id} — dimensions: "
            f"{_format_dimensions([QueryDimension(id=k, choices=v) for k, v in run.dimensions.items()])} "
            f"= {total} combinations, {run.executed_count} executed"
        )
        if identical:
            line += f" ({identical} identical)"
        first_key, first_pred = next(iter(pred_queries_by_selection.items()))
        first_result = first_pred.exec_result
        sample = [line, "", f"{first_key}:"]
        if first_result is not None and first_result.df is not None and not first_result.df.empty:
            sample.append(
                format_df(
                    first_result.df, max_visible_rows=5, max_cell_width=self.max_cell_width, floatfmt=self.floatfmt
                )
            )
            sample.append(f"({len(first_result.df)} rows)")
        elif first_result is not None and first_result.df is not None:
            sample.append("(query executed successfully, but results are empty)")
        else:
            sample.append("(statement executed successfully)")
        remaining = total - 1
        if remaining:
            zero_rows = [
                key
                for key, pred in list(pred_queries_by_selection.items())[1:]
                if pred.exec_result is not None and pred.exec_result.df is not None and pred.exec_result.df.empty
            ]
            sample.append("")
            sample.append(f"remaining combinations: {remaining}")
            if zero_rows:
                sample.append("zero-row combinations: " + ", ".join(zero_rows[:5]))
        return "\n".join(sample)
