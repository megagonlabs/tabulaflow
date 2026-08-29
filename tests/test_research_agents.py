import pytest
from pydantic import ValidationError

from tabulaflow.research.agents import SimpleAgentProtocol
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
