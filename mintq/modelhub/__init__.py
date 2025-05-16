from typing import Any
from mintq.modelhub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.modelhub.base import BaseNL2QModel
from mintq.modelhub.sql_agent_table_names_only import SQLAgentTableNamesOnly

all_model_classes = [SimpleZeroShotNL2Q, SQLAgentTableNamesOnly]

model_registry: dict[str, type[BaseNL2QModel]] = {cls.name: cls for cls in all_model_classes}  # type: ignore


def get_nl2q_model(name: str, **kwargs: Any) -> BaseNL2QModel:
    if name not in model_registry:
        raise ValueError(f"Unknown NL2Q model: {name}")
    return model_registry[name](**kwargs)


__all__ = ["get_nl2q_model", "BaseNL2QModel", "SimpleZeroShotNL2Q", "SQLAgentTableNamesOnly"]
