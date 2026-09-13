# API reference

Start with the layer you need, whether you're querying a dataset, presenting
results, or building an agent.

| Layer | APIs |
| --- | --- |
| [Core](api/core.md) | Schemas, execution results, serialization, and class registry |
| [Data](api/data.md) | Connectors, configuration, loaders, and source catalog |
| [Output](api/output.md) | Specifications, result storage, resolution, and formatting |
| [Agents](api/agents.md) | Chat sessions, tools, extraction, summarization, and traces |

The dependency order is `core <- data <- output <- agents`: each layer can
depend on those to its left. Import-linter enforces this separation. Use
connectors without an agent, or build outputs without the application UI.

Working on benchmarks or evaluation? Head to the
[research API reference](../research-toolkit/api-reference.md).
