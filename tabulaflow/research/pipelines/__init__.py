"""Outermost orchestration for running and evaluating experiments."""


def __getattr__(name: str) -> object:
    if name == "run_agent_async":
        from tabulaflow.research.pipelines.run_agent import run_agent_async

        return run_agent_async
    if name == "populate_exec_results_async":
        from tabulaflow.research.pipelines.populate_exec_results import populate_exec_results_async

        return populate_exec_results_async
    if name == "evaluate_async":
        from tabulaflow.research.pipelines.evaluate import evaluate_async

        return evaluate_async
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "run_agent_async",
    "populate_exec_results_async",
    "evaluate_async",
]
