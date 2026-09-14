# Experiment runs

An experiment run records its benchmark selection, agent configuration,
predictions, execution results, usage, and evaluation metrics. Compose the
stages in Python so each methodological choice remains visible.

## Run each stage

The [quick-start example](quick-start.md#example-build-and-evaluate-a-custom-agent)
uses the complete lifecycle:

```text
benchmark → prediction → execution → evaluation → report
```

`predict_async(...)` creates one agent per task and returns an `NL2QRunResult`.
`execute_async(...)` adds results to predicted queries. `evaluate_async(...)`
computes task metrics and run-level aggregates. Keeping the stages separate
lets you run model inference and database execution in different environments.

```python
result = await predict_async(
    agent_cls=SchemaLinkingAgent,
    agent_config=config,
    dataset=dataset,
    batch_size=8,
)

await execute_async(result, dataset, batch_size=8, timeout=60)

await evaluate_async(
    result,
    dataset,
    metrics=[BirdSQLEx(), Executable()],
    batch_size=8,
    metric_aggregators=[SimpleAverageAggregator()],
)
```

Per-task prediction failures become empty outputs so the rest of the run can
finish. Contract errors, invalid configuration, and benchmark setup failures
raise directly.

## Select tasks reproducibly

Use QIDs for an exact task set or `subsample_size` for deterministic sampling.
Record the benchmark split, selected databases, QIDs, model identifier, agent
configuration, cache policy, and TabulaFlow version with every published run.

Develop on a small selection before paying for a full split:

```python
dataset = await loader.get_split_async(
    "dev",
    databases=["california_schools"],
    subsample_size=10,
)
```

`batch_size` bounds concurrent task work. Connector configuration controls
database query concurrency, timeouts, result limits, and caching separately.

## Save and restore a run

Write the structured result, a CSV summary, and readable task reports:

```python
result.to_directory(
    "runs/schema-linking",
    eval_metrics_in_summary=["bird_sql_ex", "executable"],
)
```

The directory contains:

```text
runs/schema-linking/
├── result.json
├── result_summary.csv
└── readable/
    └── <qid>/
```

Restore the complete typed result without reconnecting to a benchmark:

```python
from pathlib import Path

from tabulaflow.research.types import NL2QRunResult

result = NL2QRunResult.model_validate_json(
    Path("runs/schema-linking/result.json").read_text()
)
```

Reconnect to the same benchmark tasks before executing unevaluated predictions
or computing metrics that need live database access.

## Compare and combine runs

Compare runs only when their benchmark, split, and task QIDs match. The
[agent comparison example](research-agents.md#example-compare-two-strategies)
holds those inputs constant while changing the prediction strategy.

`ensemble_async(...)` combines compatible candidate runs into a new run.
Majority, model-based, agent-based, and dbt-specific ensemblers are available.
Execute and evaluate the returned run through the same pipeline; individual
ensemble failures fall back to the first candidate and increment
`fallback_count`.

## Release resources

Benchmark datasets own live connectors. Close every connector in `finally`,
including when prediction or evaluation raises:

```python
try:
    result = await predict_async(...)
finally:
    await asyncio.gather(
        *(connector.close_async() for connector in dataset.db_connectors.values())
    )
```

See the [pipeline API](api/pipelines.md) for stage signatures, ensemblers, and
preprocessing workflows, or continue to [Research agents](research-agents.md).
