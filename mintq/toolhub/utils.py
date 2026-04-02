import re
from typing import Iterable, TypeVar

from pydantic import BaseModel

_M = TypeVar("_M", bound=BaseModel)


def sum_tool_metrics(metrics_iter: Iterable[_M], cls: type[_M]) -> _M:
    """Sum numeric fields across multiple metrics instances.

    Args:
        metrics_iter: Iterable of metrics objects to aggregate.
        cls: The metrics class to instantiate for the result.
    """
    totals: dict[str, int | float] = {}
    for m in metrics_iter:
        for field_name in m.model_fields:
            val = getattr(m, field_name)
            if isinstance(val, (int, float)):
                totals[field_name] = totals.get(field_name, 0) + val
    return cls(**totals)


def equals_ci(a: str | None, b: str | None) -> bool:
    """
    Compare two strings case-insensitively, treating None == None.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.lower() == b.lower()


def format_sqlalchemy_error_msg(error_msg: str) -> str:
    error_msg = re.sub(r"\[SQL:.*\]", "", error_msg, flags=re.DOTALL)
    error_msg = re.sub(r"\[parameters:.*\]", "", error_msg, flags=re.DOTALL)
    error_msg = re.sub(r"\(Background on this error at: https://sqlalche\.me/e/\S+\)", "", error_msg, flags=re.DOTALL)
    return error_msg.strip()
