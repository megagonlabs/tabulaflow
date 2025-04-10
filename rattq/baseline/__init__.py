from rattq.baseline.simple_zero_shot import SimpleZeroShotNL2Q
from rattq.baseline.base import BaseNL2QModel
from rattq.baseline.tool_agent import ToolAgentNL2Q

nl2q_model_registry = {
    "simple_zero_shot": SimpleZeroShotNL2Q,
    "tool_agent": ToolAgentNL2Q,
}


def get_nl2q_model(name: str, **kwargs) -> BaseNL2QModel:
    if name not in nl2q_model_registry:
        raise ValueError(f"Unknown NL2Q model: {name}")
    return nl2q_model_registry[name](**kwargs)


__all__ = ["get_nl2q_model", "BaseNL2QModel", "SimpleZeroShotNL2Q", "ToolAgentNL2Q"]
