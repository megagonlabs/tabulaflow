# Evaluation and analysis

| Benchmark | Primary execution metric |
| --- | --- |
| BIRD-SQL | `BirdSQLEx` |
| Spider 2.0 Snow/Lite | `Spider2Ex` |
| Spider 2.0 dbt | `Spider2DuckdbMatch` |
| CypherBench | `CypherBenchEx` |
| Beaver, ARCS, AMBROSIA | `SimpleEx` |

TabulaFlow adapts official benchmark evaluation implementations into a unified API.
See the [metric reference](api/metrics.md) for all metrics and aggregators.

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
print("Overall accuracy:", result.aggregated_eval_metrics["bird_sql_ex"]["avg"])
print("Accuracy by database:", result.aggregated_eval_metrics["bird_sql_ex_by_db"])
```

`SimpleAverageAggregator` includes zeros and excludes `None` from the average.

## Evaluate ambiguity

`SimpleEx` checks the intended interpretation; `FoundOne` checks whether the
final prediction matches any valid reference interpretation. Inspect the scores
for the first ARCS task from the [ambiguity example](agents.md#ambiguity-aware-agents):

```python
--8<-- "examples/ambiguity_aware_queries.py:evaluation-output"
```

??? example-output no-copy "Sample evaluation result"

    ```text
    --8<-- "examples/results/evaluation.txt"
    ```

## Inspect usage and latency

Inspect token usage, estimated costs, and task latency:

```python
print("Agent usage:", result.total_usage)
print("User-simulator usage:", result.total_user_simulator_usage)
print("Task latency (seconds):", result.aggregated_inference_metrics.get("latency_seconds"))
```
