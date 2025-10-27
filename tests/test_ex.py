import pytest
import pandas as pd
from mintq.metrics import SimpleEx, Spider2Ex
from mintq.schema import SimpleNL2QTaskOutput, GoldQuery, PredQuery, ExecResult


@pytest.fixture
def test_tasks() -> list[tuple[SimpleNL2QTaskOutput, float]]:
    test_cases = [
        {
            "pred_df": pd.DataFrame({"col0": [-2, 0]}),
            "gold_df": pd.DataFrame({"col0": [-2, -0.000001]}),
            "expected_score": 1.0,
        },
        {
            "pred_df": pd.DataFrame({"col0": [True, False]}),
            "gold_df": pd.DataFrame({"col0": [1, 0]}),
            "expected_score": 1.0,
        },
        {
            "pred_df": pd.DataFrame({"col0": [True, False, None]}),
            "gold_df": pd.DataFrame({"col0": [1, 0, None]}),
            "expected_score": 1.0,
        },
    ]
    return [
        (
            SimpleNL2QTaskOutput(
                qid="",
                language="",
                db="",
                question="",
                gold_query=GoldQuery(
                    query="",
                    exec_result=ExecResult(df=test_case["gold_df"]),
                ),
                pred_query=PredQuery(
                    query="",
                    exec_result=ExecResult(df=test_case["pred_df"]),
                ),
            ),
            test_case["expected_score"],
        )
        for test_case in test_cases
    ]


@pytest.mark.asyncio
async def test_spider2_ex(test_tasks: list[tuple[SimpleNL2QTaskOutput, float]]) -> None:
    spider2_ex = Spider2Ex()
    for task, expected_score in test_tasks:
        score = await spider2_ex.compute_async(task)
        assert score == expected_score


@pytest.mark.asyncio
async def test_simple_ex(test_tasks: list[tuple[SimpleNL2QTaskOutput, float]]) -> None:
    simple_ex = SimpleEx()
    for task, expected_score in test_tasks:
        score = await simple_ex.compute_async(task)
        assert score == expected_score
