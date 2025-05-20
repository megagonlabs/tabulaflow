from mintq.modelhub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.modelhub.base import BaseNL2QModel, BaseAsyncNL2QModel
from mintq.modelhub.sql_agent import SQLAgent

all_model_classes = [SimpleZeroShotNL2Q, SQLAgent]

model_registry: dict[str, type[BaseNL2QModel | BaseAsyncNL2QModel]] = {cls.name: cls for cls in all_model_classes}  # type: ignore


def get_nl2q_model_class(name: str) -> type[BaseNL2QModel | BaseAsyncNL2QModel]:
    if name not in model_registry:
        raise ValueError(f"Unknown NL2Q model: {name}")
    return model_registry[name]


__all__ = [
    "get_nl2q_model_class",
    "BaseNL2QModel",
    "BaseAsyncNL2QModel",
    "SimpleZeroShotNL2Q",
    "SQLAgent",
]
