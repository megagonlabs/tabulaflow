from mintq.modelhub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.modelhub.base import BaseNL2QModel
from mintq.modelhub.sql_agent_table_names_only import SQLAgentTableNamesOnly

nl2q_model_registry = {
    "simple_zero_shot": SimpleZeroShotNL2Q,
    "sql_agent_table_names_only": SQLAgentTableNamesOnly,
}


def get_nl2q_model(name: str, **kwargs) -> BaseNL2QModel:
    if name not in nl2q_model_registry:
        raise ValueError(f"Unknown NL2Q model: {name}")
    return nl2q_model_registry[name](**kwargs)


__all__ = ["get_nl2q_model", "BaseNL2QModel", "SimpleZeroShotNL2Q", "SQLAgentTableNamesOnly"]
