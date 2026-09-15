# Pipelines

Compose prediction, query execution, evaluation, and ensembling in Python.
See [Running experiments](../running-experiments.md) for the complete workflow
and [Preprocessing](preprocessing.md) for preparing reusable inputs.

## Prediction

`predict_async(...)` constructs one agent per task and returns an
`NL2QRunResult`. Per-task prediction failures are recorded as empty outputs so
other predictions can finish. Construction and task-contract failures can
still raise directly.

::: tabulaflow.research.pipelines.predict.predict_async

## Query execution

`execute_async(...)` populates missing reference and predicted query results in place. Pass
`force=True` to replace existing results. The per-query and per-task helpers
provide the same operation at smaller scope.

::: tabulaflow.research.pipelines.execute.execute_async

::: tabulaflow.research.query_execution.populate_query_exec_result

::: tabulaflow.research.query_execution.populate_task_exec_results

## Evaluation

`evaluate_async(...)` recomputes task evaluation metrics and aggregate scores
in place. Supply metric instances explicitly; aggregation defaults to a simple
average. It does not automatically execute missing predictions or write report
files; populate execution results first when the chosen metrics require them,
and use `NL2QRunResult.to_directory(...)` to save the run.

::: tabulaflow.research.pipelines.evaluate.evaluate_async

::: tabulaflow.research.pipelines.evaluate.compute_metrics_async

## Ensembling

`ensemble_async(...)` returns a new run from compatible candidate runs. Their
task QIDs must match the dataset. Individual ensemble failures fall back to
the first candidate and are counted in `fallback_count`.

::: tabulaflow.research.pipelines.ensemble.ensemble_async

::: tabulaflow.research.pipelines.ensemble.Ensembler

::: tabulaflow.research.agents.ensemblers.majority.MajorityEnsembler

::: tabulaflow.research.agents.ensemblers.majority.MajorityEnsemblerConfig

::: tabulaflow.research.agents.ensemblers.llm.LLMEnsembler

::: tabulaflow.research.agents.ensemblers.llm.LLMEnsemblerConfig

::: tabulaflow.research.agents.ensemblers.agent.AgentEnsembler

::: tabulaflow.research.agents.ensemblers.agent.AgentEnsemblerConfig

::: tabulaflow.research.agents.ensemblers.dbt.DbtLLMEnsembler

::: tabulaflow.research.agents.ensemblers.dbt.DbtLLMEnsemblerConfig
