from typing import Any
from mintq.metrics.base import BaseAsyncNL2QMetric
from mintq.metrics.bird_sql_ex import BirdSQLEx
from mintq.metrics.bird_sql_ex_soft import BirdSQLExSoft
from mintq.metrics.executable import Executable
from mintq.metrics.gold_executable import GoldExecutable
from mintq.metrics.gold_result_not_empty import GoldResultNotEmpty
from mintq.metrics.spider2_ex import Spider2Ex

__all__ = [
    "BaseAsyncNL2QMetric",
    "BirdSQLEx",
    "BirdSQLExSoft",
    "Executable",
    "GoldExecutable",
    "GoldResultNotEmpty",
    "Spider2Ex",
    "get_metric",
]

all_metric_classes = [
    BirdSQLEx,
    BirdSQLExSoft,
    Executable,
    GoldExecutable,
    GoldResultNotEmpty,
    Spider2Ex,
]

metric_registry: dict[str, type[BaseAsyncNL2QMetric]] = {cls.name: cls for cls in all_metric_classes}  # type: ignore


def get_metric(name: str, **kwargs: Any) -> BaseAsyncNL2QMetric:
    if name not in metric_registry:
        raise ValueError(f"Metric {name} not found")
    return metric_registry[name](**kwargs)
