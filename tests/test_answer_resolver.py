import pandas as pd
import pytest

from tabulaflow.core import (
    AnswerSpec,
    ArtifactSpec,
    ChoiceOption,
    ChoiceParameter,
    ConstantResultPlan,
    NumberParameter,
    QueryPlan,
    ResultLookupPlan,
    ResultVariant,
    SourceDef,
    TableView,
    canonical_selection_key,
)
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import AnswerResolutionError, AnswerResolver, QueryHistory, QueryHistoryResultStore


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


def _parameters() -> list[ChoiceParameter | NumberParameter]:
    return [
        ChoiceParameter(
            id="metric",
            label="Metric",
            choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
        ),
        NumberParameter(id="min_spend", label="Minimum spend", min=0, max=100_000, step=5_000, default=10_000),
    ]


@pytest.mark.asyncio
async def test_constant_result_plan_resolves_answer_artifact() -> None:
    history = await _history_with_results()
    resolver = AnswerResolver(QueryHistoryResultStore(history))
    answer = AnswerSpec(
        sources=[SourceDef(id="fixed", plan=ConstantResultPlan(result_id="Q1"))],
        artifacts=[ArtifactSpec(id="table", view=TableView(source="fixed"))],
    )

    resolved = await resolver.resolve(answer)

    record = resolved.artifacts[0].results_by_source["fixed"]
    assert resolved.selection == {}
    assert record.id == "Q1"
    assert record.db_alias == "workspace"
    assert record.query == "SELECT 1 AS a"
    assert record.row_count == 1
    assert record.columns == ["a"]


@pytest.mark.asyncio
async def test_result_lookup_plan_resolves_by_projected_selection() -> None:
    history = await _history_with_results()
    resolver = AnswerResolver(QueryHistoryResultStore(history))
    answer = AnswerSpec(
        parameters=_parameters(),
        sources=[
            SourceDef(
                id="top_customers",
                parameter_ids=["metric"],
                plan=ResultLookupPlan(
                    variants=[
                        ResultVariant(selection={"metric": "revenue"}, result_id="Q1"),
                        ResultVariant(selection={"metric": "profit"}, result_id="Q2"),
                    ]
                ),
            )
        ],
        artifacts=[ArtifactSpec(id="table", view=TableView(source="top_customers"))],
    )

    resolved = await resolver.resolve(answer, {"metric": "profit"})

    record = resolved.artifacts[0].results_by_source["top_customers"]
    assert resolved.selection == {"metric": "profit", "min_spend": 10_000}
    assert record.id == "Q2"
    assert isinstance(answer.sources[0].plan, ResultLookupPlan)
    assert canonical_selection_key({"metric": "profit"}) == canonical_selection_key(
        answer.sources[0].plan.variants[1].selection
    )


@pytest.mark.asyncio
async def test_result_lookup_plan_rejects_invalid_choice() -> None:
    history = await _history_with_results()
    resolver = AnswerResolver(QueryHistoryResultStore(history))
    answer = AnswerSpec(
        parameters=_parameters(),
        sources=[
            SourceDef(
                id="top_customers",
                parameter_ids=["metric"],
                plan=ResultLookupPlan(variants=[ResultVariant(selection={"metric": "revenue"}, result_id="Q1")]),
            )
        ],
        artifacts=[ArtifactSpec(id="table", view=TableView(source="top_customers"))],
    )

    with pytest.raises(AnswerResolutionError, match="not a valid choice"):
        await resolver.resolve(answer, {"metric": "count"})


@pytest.mark.asyncio
async def test_result_lookup_plan_reports_unavailable_selection() -> None:
    history = await _history_with_results()
    resolver = AnswerResolver(QueryHistoryResultStore(history))
    answer = AnswerSpec(
        parameters=_parameters(),
        sources=[
            SourceDef(
                id="top_customers",
                parameter_ids=["metric"],
                plan=ResultLookupPlan(variants=[ResultVariant(selection={"metric": "revenue"}, result_id="Q1")]),
            )
        ],
        artifacts=[ArtifactSpec(id="table", view=TableView(source="top_customers"))],
    )

    with pytest.raises(AnswerResolutionError, match="has no result"):
        await resolver.resolve(answer, {"metric": "profit"})


@pytest.mark.asyncio
async def test_query_plan_materialization_is_not_implemented_yet() -> None:
    history = await _history_with_results()
    resolver = AnswerResolver(QueryHistoryResultStore(history))
    answer = AnswerSpec(
        parameters=_parameters(),
        sources=[
            SourceDef(
                id="lazy",
                parameter_ids=["min_spend"],
                plan=QueryPlan(db_alias="workspace", query_template="SELECT 1"),
            )
        ],
        artifacts=[ArtifactSpec(id="table", view=TableView(source="lazy"))],
    )

    with pytest.raises(AnswerResolutionError, match="not implemented"):
        await resolver.resolve(answer, {"min_spend": 10_000})
