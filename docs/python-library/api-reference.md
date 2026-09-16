# API reference

| Layer | APIs |
| --- | --- |
| [Core](api/core.md) | Schemas, execution results, serialization, and class registry |
| [Data](api/data.md) | Connectors, configuration, loaders, and source catalog |
| [Output](api/output.md) | Specifications, result storage, resolution, and formatting |
| [Agents](api/agents.md) | Chat sessions, tools, extraction, enrichment, summarization, and traces |

The dependency order is `core <- data <- output <- agents`. Use connectors
without an agent, or build outputs without the application UI.

For benchmarks and evaluation, see the [research API reference](../research-toolkit/api-reference.md).
