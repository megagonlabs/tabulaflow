from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from tabulaflow.data import SQLConnector
from tabulaflow.research.agents import SimpleAgentProtocol
from tabulaflow.research.agents.dbt import _DbtBashTool
from tabulaflow.research.agents.direct_prompt import DirectPromptAgent
from tabulaflow.research.agents.utils import BasicAgentConfig, format_question
from tabulaflow.research.types import GoldQuery, SimpleNL2QTask


def test_format_question_appends_question_instructions() -> None:
    task = SimpleNL2QTask(
        qid="q1",
        db="db",
        question="Return one.",
        question_instructions="Use SQL.",
        gold_query=GoldQuery(query="SELECT 1"),
    )

    assert format_question(task) == "Return one.\nUse SQL."


def test_agent_config_rejects_nonpositive_max_steps() -> None:
    with pytest.raises(ValidationError):
        BasicAgentConfig(max_steps=0)


def test_concrete_agent_satisfies_extension_protocol() -> None:
    agent: SimpleAgentProtocol = DirectPromptAgent(BasicAgentConfig())

    assert agent.name == "direct_prompting"


async def test_dbt_bash_tool_releases_database_before_command(tmp_path: Path) -> None:
    class ReleaseTracker:
        calls = 0

        async def release_connections_async(self) -> None:
            self.calls += 1

    tracker = ReleaseTracker()
    tool = _DbtBashTool(cast(SQLConnector, tracker), str(tmp_path), env_overrides={})
    try:
        output = await tool.execute("printf ready", mode="kill_on_timeout")
    finally:
        await tool.close()

    assert tracker.calls == 1
    assert output == "ready\n\n[exit_code: 0]"
