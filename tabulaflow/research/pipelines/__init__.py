"""Outermost orchestration for research experiment stages."""

from importlib import import_module
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from tabulaflow.research.pipelines.ensemble import ensemble_async
    from tabulaflow.research.pipelines.evaluate import evaluate_async
    from tabulaflow.research.pipelines.execute import execute_async
    from tabulaflow.research.pipelines.predict import predict_async
    from tabulaflow.research.pipelines.preprocess import preprocess_async
    from tabulaflow.research.pipelines.run import run_experiment_async

_LAZY_EXPORTS = {
    "ensemble_async": ("tabulaflow.research.pipelines.ensemble", "ensemble_async"),
    "evaluate_async": ("tabulaflow.research.pipelines.evaluate", "evaluate_async"),
    "execute_async": ("tabulaflow.research.pipelines.execute", "execute_async"),
    "predict_async": ("tabulaflow.research.pipelines.predict", "predict_async"),
    "preprocess_async": ("tabulaflow.research.pipelines.preprocess", "preprocess_async"),
    "run_experiment_async": ("tabulaflow.research.pipelines.run", "run_experiment_async"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})


__all__ = [
    "predict_async",
    "execute_async",
    "evaluate_async",
    "ensemble_async",
    "preprocess_async",
    "run_experiment_async",
]
