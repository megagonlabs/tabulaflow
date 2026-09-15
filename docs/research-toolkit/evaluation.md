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

## Evaluate and aggregate scores

Execute predictions, then compute overall and per-database BIRD-SQL accuracy:

```python
from tabulaflow.research.metrics import BirdSQLEx, ByDBAggregator, Executable, SimpleAverageAggregator
from tabulaflow.research.pipelines import evaluate_async, execute_async

await execute_async(result, dataset, batch_size=8)
await evaluate_async(
    result,
    dataset,
    metrics=[BirdSQLEx(), Executable()],
    batch_size=8,
    metric_aggregators=[SimpleAverageAggregator(), ByDBAggregator(metric_keys=["bird_sql_ex"])],
)
print(result.aggregated_eval_metrics["bird_sql_ex"]["avg"])
print(result.aggregated_eval_metrics["bird_sql_ex_by_db"])
```

`SimpleAverageAggregator` includes zeros and excludes `None` from the average.
Report the task count and missing values with your scores.
`OfficialSplitScoreAggregator` divides by the full split size, treating missing
tasks as zero. Other aggregators group scores by difficulty or ambiguity type.
Pass `metric_aggregators=[]` to skip aggregation.

Evaluation replaces task metrics and aggregate scores. It does not execute
queries or write reports; see [saving a run](running-experiments.md#save-and-restore-a-run).

## Inspect failures

Inspect missing predictions, execution errors, and incorrect results:

```python
failed = next((task for task in result.tasks if task.eval_metrics.get("bird_sql_ex") == 0), None)
if failed is not None:
    print(failed.to_markdown())
```

Task reports show queries and results; trajectories show messages and tool calls.
Prediction tracebacks appear in logs, not empty outputs. Check reference-query
errors as well as prediction errors.

??? example-output no-copy "Sample evaluation result"

    ```text
    --8<-- "examples/results/failure.txt"
    ```

    [Download task report](../examples/results/failure-report.txt){download}

For paired comparisons, match QIDs and compare task scores. The optional
[comparison script](../examples/compare_research_agents.py) also summarizes
usage and latency.

## Inspect usage and latency

`result.total_usage` records agent usage; `result.total_user_simulator_usage`
records clarification usage.
`result.aggregated_inference_metrics` holds aggregates such as task latency.

These values depend on fields returned by each agent. Per-task latency differs
from run duration because tasks execute concurrently. Costs depend on available
model pricing; missing usage does not mean zero cost.

Report [preprocessing costs](api/preprocessing.md#prepare-reusable-inputs)
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
