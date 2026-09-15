# Pipelines

See [Running experiments](../running-experiments.md) for a complete workflow
and [Preprocessing](preprocessing.md) for preparing reusable inputs.

## Prediction

::: tabulaflow.research.pipelines.predict.predict_async

## Query execution

Populates missing reference and predicted query results in place. Pass
`force=True` to replace existing results.

::: tabulaflow.research.pipelines.execute.execute_async

::: tabulaflow.research.query_execution.populate_query_exec_result

::: tabulaflow.research.query_execution.populate_task_exec_results

## Evaluation

Replaces evaluation metrics in place. Execute queries first for execution-based
metrics; save results with `NL2QRunResult.to_directory(...)`.

::: tabulaflow.research.pipelines.evaluate.evaluate_async

::: tabulaflow.research.pipelines.evaluate.compute_metrics_async

## Ensembling

Candidate runs must share the benchmark, split, and task QIDs.

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
