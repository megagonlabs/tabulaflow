from typing import cast

import pytest

from tabulaflow.data import SQLConnector
from tabulaflow.research.agents.ambig_structured import AmbigStructuredSQLAgent
from tabulaflow.research.benchmarks.arcs import ARCSDatasetLoader
from tabulaflow.research.types import AmbigNL2QTask, GoldQuery, UserSimulatorProtocol


def test_arcs_uses_public_split_names() -> None:
    assert ARCSDatasetLoader.splits == ["test", "base"]


@pytest.mark.asyncio
async def test_gold_ambiguity_points_require_intended_resolution() -> None:
    task = AmbigNL2QTask(
        qid="q1",
        has_intended_resolution=False,
        db="db",
        question="Question",
        gold_ambiguity_points=[],
        gold_queries=[GoldQuery(query="SELECT 1")],
        gold_intended_query_id=None,
    )
    agent = AmbigStructuredSQLAgent(AmbigStructuredSQLAgent.config_cls(use_gold_ambiguity_points=True))

    with pytest.raises(ValueError, match="require a task with an intended resolution"):
        await agent.predict_async(
            task,
            cast(SQLConnector, object()),
            cast(UserSimulatorProtocol, object()),
        )
