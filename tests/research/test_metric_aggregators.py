import datetime

from tabulaflow.research.metrics.aggregators import (
    ByAmbigPointNumAggregator,
    ByAmbrosiaTaxonomyTypeAggregator,
    ByBirdSQLDifficultyAggregator,
    ByDBAggregator,
    RealScoreAggregator,
    SimpleAverageAggregator,
)
from tabulaflow.research.types import (
    ARCSAmbiguityType,
    GoldAmbiguityPointFinite,
    GoldQuery,
    NL2QRunResult,
    NL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    SimpleNL2QTaskOutput,
)


def _result(tasks: list[NL2QTaskOutput], dataset: str = "test", split: str = "test") -> NL2QRunResult:
    return NL2QRunResult(
        start_time=datetime.datetime(2026, 1, 1),
        end_time=datetime.datetime(2026, 1, 1),
        dataset=dataset,
        split=split,
        databases=list(dict.fromkeys(task.db for task in tasks)),
        subsample_size=None,
        agent="test",
        agent_config={},
        tasks=tasks,
    )


def _simple_task(
    qid: str,
    eval_metrics: dict[str, float] | None = None,
    extra_info: dict[str, object] | None = None,
) -> SimpleNL2QTaskOutput:
    return SimpleNL2QTaskOutput(
        qid=qid,
        db="db",
        question="Question",
        gold_query=GoldQuery(query="SELECT 1"),
        pred_query=None,
        eval_metrics=eval_metrics or {},
        extra_info=extra_info or {},
    )


def test_grouping_aggregators_skip_metrics_that_were_not_evaluated() -> None:
    bird = _simple_task(
        "bird",
        {"executable": 1.0},
        {"bird_sql": {"difficulty": "simple"}},
    )
    assert ByDBAggregator().aggregate(_result([bird])) == {}
    assert ByBirdSQLDifficultyAggregator().aggregate(_result([bird], dataset="bird-sql")) == {}

    ambrosia = _simple_task(
        "ambrosia",
        {"executable": 1.0},
        {"ambrosia": {"ambig_type": "scope"}},
    )
    assert ByAmbrosiaTaxonomyTypeAggregator().aggregate(_result([ambrosia], dataset="ambrosia-s")) == {}

    point = GoldAmbiguityPointFinite(
        id="A",
        phrase="value",
        ambiguity_type=ARCSAmbiguityType.semantic_value,
        interpretations=["first"],
        intended_interpretation_idx=0,
    )
    ambiguous = SimpleAmbigNL2QTaskOutput(
        qid="ambiguous",
        has_intended_resolution=True,
        db="db",
        question="value",
        gold_ambiguity_points=[point],
        gold_queries=[GoldQuery(id="GQRY-A.0", query="SELECT 1")],
        gold_intended_query_id="GQRY-A.0",
        pred_intended_query=None,
        eval_metrics={"executable": 1.0},
    )
    assert ByAmbigPointNumAggregator().aggregate(_result([ambiguous], dataset="arcs")) == {}


def test_empty_run_has_no_average_metrics() -> None:
    assert SimpleAverageAggregator().aggregate(_result([])) == {}


def test_real_score_allows_partially_missing_metrics() -> None:
    result = _result([_simple_task("q1", {"simple_ex": 1.0}), _simple_task("q2")], dataset="beaver")

    assert RealScoreAggregator().aggregate(result) == {"simple_ex_real": round(1 / 209, 4)}


def test_spider2_dbt_real_score_uses_the_official_evaluation_size() -> None:
    assert RealScoreAggregator.DATASET_CONFIGS[("spider2-dbt", "test")] == (68, "spider2_duckdb_match")
