# Evaluation and analysis

A metric scores one task output; an aggregator combines those values across an
experiment run. Use the same evaluation policy when comparing methods, then
inspect individual predictions to understand differences in their scores.

## Choose metrics

Benchmark loaders declare `default_metrics` as registry names. The Python
`evaluate_async(...)` API takes metric instances explicitly; it does not select
those defaults automatically.

| Benchmark | Primary execution metric |
| --- | --- |
| BIRD-SQL | `BirdSQLEx` |
| Spider 2.0 Snow/Lite | `Spider2Ex` |
| Spider 2.0 dbt | `Spider2DuckdbMatch` |
| CypherBench | `CypherBenchEx` |
| Beaver, ARCS, AMBROSIA-S | `SimpleEx` |

Add diagnostics that answer a specific question:

| Metric family | Question answered |
| --- | --- |
| `PredSuccess` | Did the agent produce a query? |
| `Executable` | Did the predicted query execute successfully? |
| Gold diagnostics | Can the reference query run and return data? |
| Schema-linking diagnostics | Did the method identify the relevant schema? |
| Ambiguity metrics | Did the method find valid interpretations or ambiguity points? |

Execution metrics have different comparison rules; substituting one can change
the score. See the [metric reference](api/metrics.md) for exact behavior.
Raw-prediction metrics evaluate pre-postprocessing queries and can execute them
during metric computation.

Each metric declares `compatible_output_types`. Check these against the agent's
output family when constructing an experiment; the Python evaluation stage does
not automatically filter incompatible metrics.

## Evaluate predictions

For a predicted BIRD-SQL `result` and its loaded `dataset`, first populate query
results, then evaluate:

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

The default `SimpleAverageAggregator` averages available numeric values, ignoring
`None`. A metric returning zero counts as a failure; returning `None` excludes
that value from the average. Report the task count and any missing values with
your scores.

`OfficialSplitScoreAggregator` uses the full split size for supported benchmarks,
so missing tasks count as zero. This differs from sampled-run accuracy. Other
aggregators group scores by database, BIRD-SQL difficulty, ambiguity-point count,
or AMBROSIA taxonomy.

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

For single-query outputs, distinguish missing predictions, execution errors,
and incorrect results. After execution and evaluation, inspect failed tasks:

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

Task reports include reference and predicted queries and their results. Recorded
trajectories show the model's messages and tool calls. Prediction exceptions are
logged; an empty output does not preserve the exception traceback in the run.
Also inspect reference-query errors before attributing a zero score to the agent.

For paired comparisons, match tasks by QID and compare their metric values.
Report improvements and regressions on the same task set, alongside aggregate
accuracy. The [comparison example](running-experiments.md#compare-strategies)
saves the structured outputs needed for this analysis.

## Inspect usage and latency

Usage and inference metrics are separate from evaluation scores:

```python
print("Agent usage:", result.total_usage)
print("User simulator usage:", result.total_user_simulator_usage)
print("Inference metrics:", result.aggregated_inference_metrics)
```

Agents populate task `usage`, `trajectory`, and `inference_metrics`; custom
agents should return the fields their analyses need. Built-in prediction
aggregation combines available inference values. Per-task latency differs from
wall-clock run duration because tasks execute concurrently. Estimated costs
depend on available model pricing, and missing usage should not be treated as
zero-cost inference.

When preprocessing is run separately, report that cost alongside inference.
See [reusable inputs](running-experiments.md#prepare-reusable-inputs) and
[tracing](running-experiments.md#enable-tracing) for collecting those details.

## Evaluate ambiguity

Ambiguity-aware outputs can contain an intended query, several flat
interpretations, or structured ambiguity points. These support distinct measures:

- `SimpleEx` evaluates the intended query against the intended reference.
- `FoundOne` checks whether at least one predicted interpretation matches a
  valid reference.
- Ambiguity-point metrics compare the predicted and reference structures.
- Inference metrics and simulator usage measure clarification effort and cost.

The [ambiguity example](agents.md#ambiguity-aware-agents) combines intended-query
accuracy and interpretation coverage in a complete run. Choose metrics compatible
with its output representation; those measures answer different research questions.

For a new diagnostic or aggregation policy, see
[adding a metric](extending.md#add-a-metric).
