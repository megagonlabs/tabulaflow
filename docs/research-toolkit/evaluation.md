# Evaluation

A metric scores one task output; an aggregator combines those values across an
experiment run. Metrics are independent of the agent, so compatible strategies
can be compared with the same evaluation.

## Evaluate predictions

Execute predicted queries before using execution-based metrics:

```python
await execute_async(result, dataset, batch_size=8)

await evaluate_async(
    result,
    dataset,
    metrics=[BirdSQLEx(), Executable(), PredSuccess()],
    batch_size=8,
)
```

`evaluate_async(...)` replaces each task's evaluation metrics and averages them
across the run by default. Pass an explicit aggregator list for another policy,
or an empty list to skip aggregation. It does not execute missing queries or
write reports automatically.

## Choose metrics

Benchmark loaders declare default metric names, but explicit metrics make an
experiment definition easier to review.

| Metric family | Question answered |
| --- | --- |
| Execution accuracy | Did the prediction return the accepted result? |
| Executability | Did the predicted query run successfully? |
| Prediction success | Did the agent produce a query? |
| Gold diagnostics | Can the reference query run and return data? |
| Schema-linking diagnostics | Did the agent identify the relevant schema? |
| Ambiguity metrics | Did the agent find valid interpretations or ambiguity points? |

Use the benchmark-specific execution metric for headline accuracy:
`BirdSQLEx`, `Spider2Ex`, `CypherBenchEx`, or
`Spider2DuckdbMatch`. `SimpleEx` provides a shared result comparison for
compatible SQL outputs. Raw-prediction metrics execute a query during metric
computation and are useful for diagnostics rather than as the normal pipeline.

Each metric declares compatible output types. Fail early when an explicitly
selected metric does not support the run's task family.

## Aggregate a run

`SimpleAverageAggregator` averages available task values.
`OfficialSplitScoreAggregator` divides by the benchmark's full split size, so
missing tasks count as failures. Other aggregators group selected metrics by
database, BIRD-SQL difficulty, ambiguity-point count, or AMBROSIA taxonomy.

For a sampled development run, report both the sample size and simple average;
do not present the official-split aggregate as the sample's accuracy.

Aggregated values are available directly:

```python
print(result.aggregated_eval_metrics)
```

Write selected task metrics into the CSV summary:

```python
result.to_directory(
    "runs/schema-linking",
    eval_metrics_in_summary=["bird_sql_ex", "executable"],
)
```

## Evaluate ambiguity

Ambiguity-aware outputs may contain an intended query, several flat
interpretations, or structured ambiguity points. `FoundOne` checks whether at
least one predicted interpretation matches a valid reference. Ambiguity-point
metrics compare predicted and reference structures, while inference metrics
track clarification effort and user-simulator cost.

See the [ambiguity example](research-agents.md#ambiguity-aware-agents) for a
complete structured run.

## Add a metric

A custom metric declares a unique `name`, lists its compatible output types,
and implements `compute_async(task, db_connector)`. Return one numeric value,
`None`, or a dictionary of named numeric values. A custom aggregator receives
the complete `NL2QRunResult` and returns named run-level values.

Register metrics for name-based discovery, or instantiate them directly in the
experiment script. See the [metrics API](api/metrics.md) for contracts, built-in
metrics, and aggregation operations.
