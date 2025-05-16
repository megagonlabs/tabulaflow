from mintq.metric.base import NL2QMetric
from mintq.metric.bird_sql_ex import BirdSQLEx
from mintq.metric.bird_sql_ex_soft import BirdSQLExSoft
from mintq.metric.executable import Executable
from mintq.metric.gold_executable import GoldExecutable
from mintq.metric.gold_result_not_empty import GoldResultNotEmpty
from mintq.metric.spider2_ex import Spider2Ex

__all__ = [
    "BirdSQLEx",
    "BirdSQLExSoft",
    "Executable",
    "GoldExecutable",
    "GoldResultNotEmpty",
    "Spider2Ex",
    "BaseNL2QMetric",
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

metric_registry = {cls.name: cls for cls in all_metric_classes}  # type: ignore[attr-defined]


def get_metric(name: str, **kwargs):
    if name not in metric_registry:
        raise ValueError(f"Metric {name} not found")
    return metric_registry[name](**kwargs)
