# Metrics

## Registry and contracts

A metric scores one task output; an aggregator combines scores across a run.
Metrics declare `name` and `compatible_output_types`; `compute_async(...)`
returns a number, `None`, or named values.

Pass metric instances to `evaluate_async(...)`. Loader `default_metrics` lists
their registry names; the Python API does not select them automatically or
filter incompatible output types. Check `compatible_output_types` against the
agent's output family.

::: tabulaflow.research.metrics.registry.metric_registry

::: tabulaflow.research.metrics.registry.MetricProtocol

::: tabulaflow.research.metrics.registry.MetricAggregatorProtocol

::: tabulaflow.research.types.NumericOrNull

## Execution comparison

See [Evaluation and analysis](../evaluation.md) for benchmark metrics.

::: tabulaflow.research.metrics.simple_ex.SimpleEx

::: tabulaflow.research.metrics.bird_sql_ex.BirdSQLEx

::: tabulaflow.research.metrics.bird_sql_ex_soft.BirdSQLExSoft

::: tabulaflow.research.metrics.spider2_ex.Spider2Ex

::: tabulaflow.research.metrics.spider2_duckdb_match.Spider2DuckdbMatch

::: tabulaflow.research.metrics.cypherbench_ex.CypherBenchEx

## Prediction and execution diagnostics

`PredSuccess` checks whether a query was produced; `Executable` checks whether
it executed successfully. Gold diagnostics check reference-query execution and
nonempty results. Raw-prediction metrics evaluate queries from before postprocessing.

::: tabulaflow.research.metrics.pred_success.PredSuccess

::: tabulaflow.research.metrics.executable.Executable

::: tabulaflow.research.metrics.gold_executable.GoldExecutable

::: tabulaflow.research.metrics.gold_result_not_empty.GoldResultNotEmpty

::: tabulaflow.research.metrics.raw_pred_simple_ex.RawPredSimpleEx

::: tabulaflow.research.metrics.raw_pred_bird_sql_ex.RawPredBirdSQLEx

::: tabulaflow.research.metrics.schema_linking_stats.SchemaLinkingStats

## Ambiguity metrics

`SimpleEx` compares the final prediction with the intended reference; `FoundOne`
accepts any valid reference interpretation. Ambiguity-point metrics measure
which phrases and interpretations the agent identified.

::: tabulaflow.research.metrics.ambig_point_stats.AmbigPointStats

::: tabulaflow.research.metrics.gold_ambig_point_stats.GoldAmbigPointStats

::: tabulaflow.research.metrics.found_one.FoundOne

::: tabulaflow.research.metrics.psjs.PSJS

## Aggregators

Pass aggregators to `evaluate_async(..., metric_aggregators=[...])`.
The default is `SimpleAverageAggregator()`; pass `[]` to skip aggregation.

`SimpleAverageAggregator` includes zeros and excludes `None` from the average.
`OfficialSplitScoreAggregator` divides by the configured full split size,
treating missing tasks as zero. Other aggregators group scores by database,
difficulty, or ambiguity type. Report the task count and missing values with scores.

For paired comparisons, match QIDs and compare task scores. The optional
[comparison script](../../examples/compare_research_agents.py) also summarizes
usage and latency.

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

## Custom metrics and aggregators

See [Add a metric](../extending.md#add-a-metric) for a complete implementation.
Metrics can also return a dictionary whose keys become task metric names.
Register with `metric_registry.register(YourMetric)` for name-based lookup.

A custom aggregator implements `aggregate(result: NL2QRunResult)` and returns
named run-level values. Pass it in `metric_aggregators`, including
`SimpleAverageAggregator()` if you also want averages. See
[aggregation](../evaluation.md#evaluate-and-aggregate-scores) and the
[metric contracts](#registry-and-contracts).
