# Metrics

A metric computes values for one task output. An aggregator combines task
values into run-level scores. Both are independent of the prediction strategy.

## Registry and contracts

Registered metrics declare `name` and `compatible_output_types`. Their
`compute_async(...)` method returns a numeric value, `None`, or a dictionary
of named values. Select metrics compatible with your task output family when
calling the evaluation API directly.

::: tabulaflow.research.metrics.registry.metric_registry

::: tabulaflow.research.metrics.registry.MetricProtocol

::: tabulaflow.research.metrics.registry.MetricAggregatorProtocol

::: tabulaflow.research.types.NumericOrNull

## Execution comparison

Use the benchmark loader's `default_metrics` to discover its default metric
selection. The implementations below define their individual comparison rules.

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

Aggregators consume `NL2QRunResult` and return named aggregate values. Use an
explicit list of aggregators with `evaluate_async(...)`.

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
