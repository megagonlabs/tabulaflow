import pandas as pd
import pytest

from tabulaflow.core import (
    ChoiceOption,
    ChoiceParameter,
    ConstantResultPlan,
    NumberParameter,
    ParameterDef,
    QueryPlan,
    ResultLookupPlan,
    ResultVariant,
    SourceDef,
    canonical_selection_key,
)
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import QueryHistory, QueryHistoryResultStore, SourceResolutionError, SourceResolver


async def _history_with_results() -> QueryHistory:
    history = QueryHistory()
    await history.add(
        "workspace",
        "sql",
        PredQuery(query="SELECT 1 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [1]}))),
    )
    await history.add(
        "workspace",
        "sql",
        PredQuery(query="SELECT 2 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [2]}))),
    )
    return history


def _parameters() -> dict[str, ParameterDef]:
    return {
        "metric": ChoiceParameter(
            id="metric",
            label="Metric",
            choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
        ),
        "min_spend": NumberParameter(
            id="min_spend", label="Minimum spend", min=0, max=100_000, step=5_000, default=10_000
        ),
    }


@pytest.mark.asyncio
async def test_constant_result_plan_resolves_existing_result() -> None:
    history = await _history_with_results()
    resolver = SourceResolver(QueryHistoryResultStore(history))
    source = SourceDef(id="fixed", plan=ConstantResultPlan(result_id="Q1"))

    record = await resolver.resolve(source, parameters={}, selection={})

    assert record.id == "Q1"
    assert record.db_alias == "workspace"
    assert record.query == "SELECT 1 AS a"
    assert record.row_count == 1
    assert record.columns == ["a"]


@pytest.mark.asyncio
async def test_result_lookup_plan_resolves_by_projected_selection() -> None:
    history = await _history_with_results()
    resolver = SourceResolver(QueryHistoryResultStore(history))
    source = SourceDef(
        id="top_customers",
        parameter_ids=["metric"],
        plan=ResultLookupPlan(
            variants=[
                ResultVariant(selection={"metric": "revenue"}, result_id="Q1"),
                ResultVariant(selection={"metric": "profit"}, result_id="Q2"),
            ]
        ),
    )

    record = await resolver.resolve(source, parameters=_parameters(), selection={"metric": "profit", "unused": True})

    assert record.id == "Q2"
    assert canonical_selection_key({"metric": "profit"}) == canonical_selection_key(
        source.plan.variants[1].selection
    )


@pytest.mark.asyncio
async def test_result_lookup_plan_rejects_invalid_choice() -> None:
    history = await _history_with_results()
    resolver = SourceResolver(QueryHistoryResultStore(history))
    source = SourceDef(
        id="top_customers",
        parameter_ids=["metric"],
        plan=ResultLookupPlan(variants=[ResultVariant(selection={"metric": "revenue"}, result_id="Q1")]),
    )

    with pytest.raises(SourceResolutionError, match="not a valid choice"):
        await resolver.resolve(source, parameters=_parameters(), selection={"metric": "count"})


@pytest.mark.asyncio
async def test_result_lookup_plan_reports_unavailable_selection() -> None:
    history = await _history_with_results()
    resolver = SourceResolver(QueryHistoryResultStore(history))
    source = SourceDef(
        id="top_customers",
        parameter_ids=["metric"],
        plan=ResultLookupPlan(variants=[ResultVariant(selection={"metric": "revenue"}, result_id="Q1")]),
    )

    with pytest.raises(SourceResolutionError, match="has no result"):
        await resolver.resolve(source, parameters=_parameters(), selection={"metric": "profit"})


@pytest.mark.asyncio
async def test_query_plan_materialization_is_not_implemented_yet() -> None:
    history = await _history_with_results()
    resolver = SourceResolver(QueryHistoryResultStore(history))
    source = SourceDef(
        id="lazy",
        parameter_ids=["min_spend"],
        plan=QueryPlan(db_alias="workspace", query_template="SELECT 1"),
    )

    with pytest.raises(SourceResolutionError, match="not implemented"):
        await resolver.resolve(source, parameters=_parameters(), selection={"min_spend": 10_000})
