from mintq.metric.base import NL2QMetric
from mintq.metric.bird_sql_ex import BirdSQLEx
from mintq.metric.bird_sql_ex_soft import BirdSQLExSoft
from mintq.metric.executable import Executable
from mintq.metric.gold_executable import GoldExecutable
from mintq.metric.gold_result_not_empty import GoldResultNotEmpty

__all__ = [
    "BirdSQLEx",
    "BirdSQLExSoft",
    "Executable",
    "GoldExecutable",
    "GoldResultNotEmpty",
]


metric_registry = {
    "bird_sql_ex": BirdSQLEx,
    "bird_sql_ex_soft": BirdSQLExSoft,
    "executable": Executable,
    "gold_executable": GoldExecutable,
    "gold_result_not_empty": GoldResultNotEmpty,
}


def get_metric(name: str, **kwargs) -> NL2QMetric:
    if name not in metric_registry:
        raise ValueError(f"Metric {name} not found")
    return metric_registry[name](**kwargs)
