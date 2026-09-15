# Metrics

## Registry and contracts

Metrics declare `name` and `compatible_output_types`; `compute_async(...)`
returns a number, `None`, or named values. See
[adding a metric](../extending.md#add-a-metric) for an example.

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
