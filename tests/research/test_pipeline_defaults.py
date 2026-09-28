import inspect
from collections.abc import Callable

from tabulaflow.research.cli import run_benchmark
from tabulaflow.research.pipelines import DEFAULT_BATCH_SIZE
from tabulaflow.research.pipelines.ensemble import ensemble_async
from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.pipelines.execute import execute_async
from tabulaflow.research.pipelines.predict import predict_async
from tabulaflow.research.pipelines.run import run_experiment_async


def test_python_pipeline_batch_size_defaults_are_consistent() -> None:
    functions: list[Callable[..., object]] = [
        run_experiment_async,
        predict_async,
        execute_async,
        evaluate_async,
        ensemble_async,
    ]

    assert DEFAULT_BATCH_SIZE == 64
    assert all(
        inspect.signature(function).parameters["batch_size"].default == DEFAULT_BATCH_SIZE for function in functions
    )


def test_benchmark_cli_uses_pipeline_batch_size_default() -> None:
    option = inspect.signature(run_benchmark).parameters["batch_size"].default

    assert option.default == DEFAULT_BATCH_SIZE
