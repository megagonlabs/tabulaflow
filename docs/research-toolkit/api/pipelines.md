# Pipelines

See [Running experiments](../running-experiments.md) for saving and scaling runs
and [Preprocessing](preprocessing.md) for preparing reusable inputs.

## Prediction

Creates one agent per task and returns an `NL2QRunResult` after all batches;
it does not checkpoint each batch. Calling it again starts fresh inference.

Prediction exceptions are logged and recorded as empty outputs. Construction
and task-contract errors propagate. For project-based tasks, see the
[dbt strategy](agents.md#dbt-strategy).

::: tabulaflow.research.pipelines.predict.predict_async

## Query execution

Populates missing reference and predicted query results in place. Pass
`force=True` to replace existing results. Query errors are recorded in
`ExecResult.error`.

::: tabulaflow.research.pipelines.execute.execute_async

::: tabulaflow.research.query_execution.populate_query_exec_result

::: tabulaflow.research.query_execution.populate_task_exec_results

## Evaluation

Replaces evaluation metrics in place. Execute queries first for execution-based
metrics and pass the complete metric list on each call. Evaluation errors
propagate. Save results with `NL2QRunResult.to_directory(...)`.

::: tabulaflow.research.pipelines.evaluate.evaluate_async

::: tabulaflow.research.pipelines.evaluate.compute_metrics_async

## Ensembling

Candidate runs must share the benchmark, split, and task QIDs, with an output
family supported by the ensembler. Task-level exceptions fall back to the
first candidate and increment `aggregated_inference_metrics["fallback_count"]`.

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
