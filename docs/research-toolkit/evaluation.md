# Evaluation and analysis

A metric scores one task output; an aggregator combines scores across a run.

## Choose metrics

Pass metric instances to `evaluate_async(...)`. Loader `default_metrics` lists
their registry names; the Python API does not select them automatically.

| Benchmark | Primary execution metric |
| --- | --- |
| BIRD-SQL | `BirdSQLEx` |
| Spider 2.0 Snow/Lite | `Spider2Ex` |
| Spider 2.0 dbt | `Spider2DuckdbMatch` |
| CypherBench | `CypherBenchEx` |
| Beaver, ARCS, AMBROSIA-S | `SimpleEx` |

Diagnostics:

| Metric family | Question answered |
| --- | --- |
| `PredSuccess` | Did the agent produce a query? |
| `Executable` | Did the predicted query execute successfully? |
| Gold diagnostics | Can the reference query run and return data? |
| Schema-linking diagnostics | Did the method identify the relevant schema? |
| Ambiguity metrics | Did the method find valid interpretations or ambiguity points? |

See the [metric reference](api/metrics.md) for comparison rules. Raw-prediction
metrics execute and evaluate queries from before postprocessing.

Check `compatible_output_types` against the agent's output family; the Python
API does not filter incompatible metrics.

## Evaluate predictions

Execute the BIRD-SQL predictions before computing execution accuracy:

```python
from tabulaflow.research.metrics import BirdSQLEx, Executable, PredSuccess
from tabulaflow.research.pipelines import evaluate_async, execute_async

await execute_async(result, dataset, batch_size=8)
await evaluate_async(
    result,
    dataset,
    metrics=[BirdSQLEx(), Executable(), PredSuccess()],
    batch_size=8,
)
print(result.aggregated_eval_metrics["bird_sql_ex"]["avg"])
```

`evaluate_async(...)` replaces each task's evaluation metrics and the run's
aggregate scores. It does not execute missing queries or write reports.
See [Running experiments](running-experiments.md#save-a-run) for persistence and
continuing from saved predictions.

## Aggregate scores

`SimpleAverageAggregator` includes zeros and excludes `None` from the average.
Report the task count and missing values with your scores.

`OfficialSplitScoreAggregator` divides by the full split size, treating missing
tasks as zero. Other aggregators group scores by database, BIRD-SQL difficulty,
ambiguity-point count, or AMBROSIA taxonomy.

For a BIRD-SQL database breakdown, request the metric key explicitly:

```python
from tabulaflow.research.metrics import ByDBAggregator, SimpleAverageAggregator

await evaluate_async(
    result,
    dataset,
    metrics=[BirdSQLEx(), Executable(), PredSuccess()],
    batch_size=8,
    metric_aggregators=[
        SimpleAverageAggregator(),
        ByDBAggregator(metric_keys=["bird_sql_ex"]),
    ],
)
print(result.aggregated_eval_metrics["bird_sql_ex_by_db"])
```

Pass `metric_aggregators=[]` to compute task scores without aggregation.

## Inspect failures

Inspect missing predictions, execution errors, and incorrect results:

```python
from tabulaflow.research.types import SimpleNL2QTaskOutput

for task in result.tasks:
    if not isinstance(task, SimpleNL2QTaskOutput):
        continue
    if task.eval_metrics.get("bird_sql_ex") == 1:
        continue
    print(task.qid, task.question, task.eval_metrics)
    if task.pred_query is None:
        print("No prediction; inspect the prediction log.")
    elif task.pred_query.exec_result is None:
        print("Query has not been executed.")
    elif task.pred_query.exec_result.error is not None:
        print(task.pred_query.exec_result.error.message)
    print(task.to_markdown())
```

Task reports show queries and results; trajectories show messages and tool calls.
Prediction tracebacks appear in logs, not empty outputs. Check reference-query
errors as well as prediction errors.

For paired comparisons, match QIDs and compare task scores. The
[comparison example](running-experiments.md#compare-strategies) saves these outputs.

## Inspect usage and latency

Usage and inference metrics are separate from evaluation scores:

```python
print("Agent usage:", result.total_usage)
print("User simulator usage:", result.total_user_simulator_usage)
print("Inference metrics:", result.aggregated_inference_metrics)
```

These aggregates use the fields returned by each agent. Per-task latency differs
from run duration because tasks execute concurrently. Costs depend on available
model pricing; missing usage does not mean zero cost.

Report [preprocessing costs](running-experiments.md#prepare-reusable-inputs)
separately. For detailed model activity, [enable tracing](running-experiments.md#enable-tracing).

## Evaluate ambiguity

- `SimpleEx` evaluates the intended query against the intended reference.
- `FoundOne` checks whether at least one predicted interpretation matches a
  valid reference.
- Ambiguity-point metrics compare the predicted and reference structures.
- Inference metrics and simulator usage measure clarification effort and cost.

The [ambiguity example](agents.md#ambiguity-aware-agents) measures intended-query
accuracy and interpretation coverage.

For a new diagnostic or aggregation policy, see
[adding a metric](extending.md#add-a-metric).
