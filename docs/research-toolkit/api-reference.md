# API reference

Start with the part of an experiment you want to extend. Signatures, fields,
and methods are generated from the source.

| Area | APIs |
| --- | --- |
| [Tasks and runs](api/types.md) | Queries, task families, predictions, datasets, and serialized runs |
| [Benchmarks](api/benchmarks.md) | Loader protocol, dataset registry, task selection, installation, and runtimes |
| [Agents](api/agents.md) | Strategy protocols, built-in agents, configurations, user simulation, and research tools |
| [Metrics](api/metrics.md) | Metric protocol, registered metrics, and aggregation policies |
| [Pipelines and preprocessing](api/pipelines.md) | Prediction, execution, evaluation, ensembling, and preprocessing |

Research uses the shared [library APIs](../python-library/api-reference.md)
for connections, schemas, execution results, tools, and model infrastructure.
For example, `PredQuery.exec_result` contains the library's `ExecResult`, while
`SimpleNL2QTaskOutput` adds benchmark-specific prediction and evaluation fields.

The APIs listed here form the documented research surface. Internal helpers
and command-line argument parsers are not extension contracts. Start with the
[quick start](quick-start.md) for a complete experiment.
