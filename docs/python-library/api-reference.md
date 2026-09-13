# API reference

Start with the layer you need, whether you're querying a dataset, presenting
results, or building an agent.

| Layer | Purpose |
| --- | --- |
| [Core](api/core.md) | Shared schemas, execution results, and DataFrame serialization. |
| [Data](api/data.md) | A common connector interface for SQL, Neo4j, SPARQL, files, and datasets. Each backend keeps its query language. |
| [Output](api/output.md) | Store results and define parameterized tables, charts, maps, and graphs for your frontend. |
| [Agents](api/agents.md) | Chat sessions with streaming text, tool progress, and usage events, plus reusable tools, extraction, and summarization. |

You can also add your own connectors, tools, and schema formatters through
the documented protocols and registries.

## How the layers fit

Use connectors without an agent, or build outputs without the application UI.

```text
Core <- Data <- Output <- Agents
```

Each layer can depend on layers to its left. Import-linter enforces this
separation.

## Imports

Import shared types from `tabulaflow.core`, connector entry points from
`tabulaflow.data`, and `ChatSession` and `ChatInput` from `tabulaflow.agents`.
For specialized APIs, use submodules such as `tabulaflow.output.specs` or
`tabulaflow.agents.extraction`.

Working on benchmarks or evaluation? Head to the
[research API reference](../research-toolkit/api-reference.md).
