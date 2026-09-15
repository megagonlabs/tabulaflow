# Metrics

## Registry and contracts

Metrics declare `name` and `compatible_output_types`; `compute_async(...)`
returns a number, `None`, or named values. See
[the example below](#example-add-a-metric) for an example.

::: tabulaflow.research.metrics.registry.metric_registry

::: tabulaflow.research.metrics.registry.MetricProtocol

::: tabulaflow.research.metrics.registry.MetricAggregatorProtocol

::: tabulaflow.research.types.NumericOrNull

## Execution comparison

See [metric selection](../evaluation.md#choose-metrics) for benchmark defaults.

::: tabulaflow.research.metrics.simple_ex.SimpleEx

::: tabulaflow.research.metrics.bird_sql_ex.BirdSQLEx

::: tabulaflow.research.metrics.bird_sql_ex_soft.BirdSQLExSoft

::: tabulaflow.research.metrics.spider2_ex.Spider2Ex

::: tabulaflow.research.metrics.spider2_duckdb_match.Spider2DuckdbMatch

::: tabulaflow.research.metrics.cypherbench_ex.CypherBenchEx

## Prediction and execution diagnostics

::: tabulaflow.research.metrics.pred_success.PredSuccess

::: tabulaflow.research.metrics.executable.Executable

::: tabulaflow.research.metrics.gold_executable.GoldExecutable

::: tabulaflow.research.metrics.gold_result_not_empty.GoldResultNotEmpty

::: tabulaflow.research.metrics.raw_pred_simple_ex.RawPredSimpleEx

::: tabulaflow.research.metrics.raw_pred_bird_sql_ex.RawPredBirdSQLEx

::: tabulaflow.research.metrics.schema_linking_stats.SchemaLinkingStats

## Ambiguity metrics

::: tabulaflow.research.metrics.ambig_point_stats.AmbigPointStats

::: tabulaflow.research.metrics.gold_ambig_point_stats.GoldAmbigPointStats

::: tabulaflow.research.metrics.found_one.FoundOne

::: tabulaflow.research.metrics.psjs.PSJS

## Aggregators

Pass aggregators to `evaluate_async(..., metric_aggregators=[...])`.

::: tabulaflow.research.metrics.aggregators.SimpleAverageAggregator

::: tabulaflow.research.metrics.aggregators.OfficialSplitScoreAggregator

::: tabulaflow.research.metrics.aggregators.SimpleInferenceMetricsAggregator

::: tabulaflow.research.metrics.aggregators.ByDBAggregator

::: tabulaflow.research.metrics.aggregators.ByAmbigPointNumAggregator

::: tabulaflow.research.metrics.aggregators.ByAmbrosiaTaxonomyTypeAggregator

::: tabulaflow.research.metrics.aggregators.ByBirdSQLDifficultyAggregator

## Aggregation values and operations

`aggregate_metrics` combines scalar or consistently nested values without
requiring an `NL2QRunResult`.

::: tabulaflow.research.metrics.aggregators.aggregate_metrics

::: tabulaflow.research.metrics.aggregators.AggregationOp

::: tabulaflow.research.metrics.aggregators.MetricValue

## Example: Add a metric

A metric declares `name` and `compatible_output_types`, and implements
`compute_async(task, db_connector)`. This diagnostic counts returned rows:

```python
from typing import ClassVar

from tabulaflow.data import DataConnector
from tabulaflow.research.types import NL2QTaskOutput, SimpleNL2QTaskOutput


class ReturnedRows:
    name: ClassVar[str] = "returned_rows"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: DataConnector | None = None
    ) -> int | None:
        if not isinstance(task, SimpleNL2QTaskOutput):
            raise TypeError("ReturnedRows requires a single-query output.")
        query = task.pred_query
        if query is None or query.exec_result is None:
            return None
        result = query.exec_result
        if result.error is not None or result.df is None:
            return None
        return len(result.df)
```

Pass an instance alongside the accuracy metric:

```python
from tabulaflow.research.metrics import SimpleEx
from tabulaflow.research.pipelines import evaluate_async

await evaluate_async(result, dataset, metrics=[SimpleEx(), ReturnedRows()], batch_size=8)
```

Zero means an empty result; `None` is excluded from the average. Metrics can also
return a dictionary whose keys become task metric names. Register with
`metric_registry.register(ReturnedRows)` for name-based lookup.

A custom aggregator implements `aggregate(result: NL2QRunResult)` and returns
named run-level values. Pass it in `metric_aggregators`, including
`SimpleAverageAggregator()` if you also want averages. See
[aggregation](../evaluation.md#evaluate-and-aggregate-scores) and the
[metric contracts](#registry-and-contracts).
