"""Outermost orchestration for research experiment stages."""


def __getattr__(name: str) -> object:
    if name == "predict_async":
        from tabulaflow.research.pipelines.predict import predict_async

        return predict_async
    if name == "execute_async":
        from tabulaflow.research.pipelines.execute import execute_async

        return execute_async
    if name == "evaluate_async":
        from tabulaflow.research.pipelines.evaluate import evaluate_async

        return evaluate_async
    if name == "ensemble_async":
        from tabulaflow.research.pipelines.ensemble import ensemble_async

        return ensemble_async
    if name == "preprocess_async":
        from tabulaflow.research.pipelines.preprocess import preprocess_async

        return preprocess_async
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "predict_async",
    "execute_async",
    "evaluate_async",
    "ensemble_async",
    "preprocess_async",
]
