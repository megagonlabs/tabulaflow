from rattq.baseline.simple_zero_shot import SimpleZeroShotNL2Q
from rattq.baseline.base import BaseNL2QModel


def get_nl2q_model(name: str, **kwargs) -> BaseNL2QModel:
    if name == "simple_zero_shot":
        return SimpleZeroShotNL2Q(**kwargs)
    else:
        raise ValueError(f"Unknown NL2Q model: {name}")


__all__ = ["get_nl2q_model", "BaseNL2QModel", "SimpleZeroShotNL2Q"]
