from typing import Any, cast

import pandas as pd
import pytest
from pydantic import ValidationError

from tabulaflow.core import ErrorInfo, ExecResult
from tabulaflow.data import DBConnector
from tabulaflow.research.agents.simple_zero_shot import SimpleZeroShotNL2Q, SimpleZeroShotNL2QConfig
from tabulaflow.research.agents.utils import BasicAgentConfig, format_question
from tabulaflow.research.types import GoldQuery, SimpleNL2QTask


class _Connector:
    def __init__(self, results: dict[str, ExecResult]) -> None:
        self.results = results

    async def run_query_async(self, query: str) -> ExecResult:
        return self.results[query]


def test_format_question_appends_question_instructions() -> None:
    task = SimpleNL2QTask(
        qid="q1",
        db="db",
        question="Return one.",
        question_instructions="Use SQL.",
        gold_query=GoldQuery(query="SELECT 1"),
    )

    assert format_question(task) == "Return one.\nUse SQL."


@pytest.mark.parametrize(
    ("config_type", "kwargs"),
    [
        (BasicAgentConfig, {"max_steps": 0}),
        (SimpleZeroShotNL2QConfig, {"num_candidates": 0}),
    ],
)
def test_agent_config_rejects_nonpositive_counts(config_type: type[Any], kwargs: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        config_type(**kwargs)


async def test_zero_shot_selects_candidate_from_majority_execution_result() -> None:
    connector = _Connector(
        {
            "q1": ExecResult(df=pd.DataFrame({"value": [1]})),
            "q2": ExecResult(df=pd.DataFrame({"value": [1]})),
            "q3": ExecResult(df=pd.DataFrame({"value": [2]})),
        }
    )
    agent = SimpleZeroShotNL2Q(SimpleZeroShotNL2QConfig())

    selected = await agent.select_best_query_async(["q1", "q2", "q3"], cast(DBConnector, connector))

    assert selected == 0


async def test_zero_shot_ignores_failed_and_empty_results() -> None:
    connector = _Connector(
        {
            "failed": ExecResult(error=ErrorInfo(exc_type="Error", message="failed")),
            "empty": ExecResult(df=pd.DataFrame({"value": []})),
            "valid": ExecResult(df=pd.DataFrame({"value": [1]})),
        }
    )
    agent = SimpleZeroShotNL2Q(SimpleZeroShotNL2QConfig())

    selected = await agent.select_best_query_async(["failed", "empty", "valid"], cast(DBConnector, connector))

    assert selected == 2
