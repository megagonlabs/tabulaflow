import pytest
import pandas as pd
import numpy as np
import math
from pydantic import BaseModel
from mintq.metrics import SimpleEx, Spider2Ex
from mintq.schema import SimpleNL2QTaskOutput, GoldQuery, PredQuery, ExecResult, NL2QTaskOutput


class ExampleCase(BaseModel):
    task: NL2QTaskOutput
    simple_ex_expected_score: float
    spider2_ex_expected_score: float


@pytest.fixture
def examples() -> list[ExampleCase]:
    test_cases = [
        {
            "qid": "test_1",
            "pred_df": pd.DataFrame({"col0": [None, None, None, None]}),
            "gold_df": pd.DataFrame({"col0": [math.nan, np.nan, "nan", None]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,  # without csv roundtrip, spider2_ex is 0.0
        },
        {
            "qid": "test_2",
            "pred_df": pd.DataFrame({"col0": [1, 2, 2]}),
            "gold_df": pd.DataFrame({"col0": [1, 2]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 0.0,
        },
        {
            "qid": "test_3",
            "pred_df": pd.DataFrame({"col0": [np.nan, 2]}),
            "gold_df": pd.DataFrame({"col0": [math.nan, 2]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,
        },
        {
            "qid": "test_4",
            "pred_df": pd.DataFrame({"col0": [np.nan, 2]}),
            "gold_df": pd.DataFrame({"col0": [math.nan, 2]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,
        },
        {
            "qid": "test_5",
            "pred_df": pd.DataFrame({"col0": ["2.0", "1e2"]}),
            "gold_df": pd.DataFrame({"col0": [2, 100]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,  # without csv roundtrip, spider2_ex is 0.0
        },
        {
            "qid": "test_6",
            "pred_df": pd.DataFrame({"col0": [-2, 0]}),
            "gold_df": pd.DataFrame({"col0": [-2, -0.000001]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 0.0,
        },
        {
            "qid": "test_7",
            "pred_df": pd.DataFrame({"col0": [True, False]}),
            "gold_df": pd.DataFrame({"col0": [1, 0]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,
        },
        {
            "qid": "test_8",
            "pred_df": pd.DataFrame({"col0": [True, False, None]}),
            "gold_df": pd.DataFrame({"col0": [1, 0, None]}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,
        },
        {
            "qid": "test_9",
            "pred_df": pd.DataFrame({"col0": []}),
            "gold_df": pd.DataFrame({"col1": []}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,
        },
        {
            "qid": "test_10",
            "pred_df": pd.DataFrame({"col0": []}),
            "gold_df": pd.DataFrame({"col0": [], "col1": []}),
            "simple_ex_expected_score": 0.0,
            "spider2_ex_expected_score": 1.0,
        },
        {
            "qid": "test_11",
            "pred_df": pd.DataFrame({"col0": [], "col1": []}),
            "gold_df": pd.DataFrame({"col0": []}),
            "simple_ex_expected_score": 1.0,
            "spider2_ex_expected_score": 1.0,
        },
    ]
    return [
        ExampleCase(
            task=SimpleNL2QTaskOutput(
                qid=test_case["qid"],
                language="sqlite",
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
            simple_ex_expected_score=test_case["simple_ex_expected_score"],
            spider2_ex_expected_score=test_case["spider2_ex_expected_score"],
        )
        for test_case in test_cases
    ]


@pytest.mark.asyncio
async def test_spider2_ex(examples: list[ExampleCase]) -> None:
    spider2_ex = Spider2Ex()
    for example in examples:
        score = await spider2_ex.compute_async(example.task, None)  # type: ignore[arg-type]
        assert score == example.spider2_ex_expected_score


@pytest.mark.asyncio
async def test_simple_ex(examples: list[ExampleCase]) -> None:
    simple_ex = SimpleEx()
    for example in examples:
        score = await simple_ex.compute_async(example.task, None)  # type: ignore[arg-type]
        assert score == example.simple_ex_expected_score
