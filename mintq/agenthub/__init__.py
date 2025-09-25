from mintq.agenthub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.agenthub.base import BaseAsyncNL2QAgent
from mintq.agenthub.sql_agent import SQLAgent
from mintq.agenthub.sql_agent_v2 import SQLAgentV2
from mintq.agenthub.sql_multi_agent_v1 import SQLMultiAgentV1
from mintq.agenthub.ambig_simple import AmbigSimpleSQLAgent

all_model_classes = [SimpleZeroShotNL2Q, SQLAgent, SQLAgentV2, SQLMultiAgentV1, AmbigSimpleSQLAgent]

model_registry: dict[str, type[BaseAsyncNL2QAgent]] = {cls.name: cls for cls in all_model_classes}  # type: ignore


def get_nl2q_agent_class(name: str) -> type[BaseAsyncNL2QAgent]:
    if name not in model_registry:
        raise ValueError(f"Unknown NL2Q model: {name}")
    return model_registry[name]


__all__ = [
    "get_nl2q_agent_class",
    "BaseAsyncNL2QAgent",
    "SimpleZeroShotNL2Q",
    "SQLAgent",
    "SQLAgentV2",
    "SQLMultiAgentV1",
    "AmbigSimpleSQLAgent",
]
