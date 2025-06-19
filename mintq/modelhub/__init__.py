from mintq.modelhub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.modelhub.base import BaseAsyncNL2QModel
from mintq.modelhub.sql_agent import SQLAgent
from mintq.modelhub.sql_agent_v1 import SQLAgentV1

all_model_classes = [SimpleZeroShotNL2Q, SQLAgent, SQLAgentV1]

model_registry: dict[str, type[BaseAsyncNL2QModel]] = {cls.name: cls for cls in all_model_classes}  # type: ignore


def get_nl2q_model_class(name: str) -> type[BaseAsyncNL2QModel]:
    if name not in model_registry:
        raise ValueError(f"Unknown NL2Q model: {name}")
    return model_registry[name]


__all__ = [
    "get_nl2q_model_class",
    "BaseAsyncNL2QModel",
    "SimpleZeroShotNL2Q",
    "SQLAgent",
    "SQLAgentV1",
]
