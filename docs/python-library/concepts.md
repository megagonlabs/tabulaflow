# Concepts

TabulaFlow separates data access, output presentation, and agent execution so
you can use its components without adopting the whole application.

## How the layers fit

```text
Core <- Data <- Output <- Agents
```

Each layer can depend on layers to its left. Import-linter enforces this
separation. Use connectors without an agent, or build outputs without the
application UI.

## Imports

Import shared types from `tabulaflow.core`, connector entry points from
`tabulaflow.data`, and `ChatSession` and `ChatInput` from `tabulaflow.agents`.
For specialized APIs, use submodules such as `tabulaflow.output.specs` or
`tabulaflow.agents.extraction`.

## Extension points

Add your own [connectors](api/data.md#connector-interface),
[tools](api/agents.md#tool-contracts), and
[schema formatters](api/output.md#custom-schema-formatters) through the
documented protocols and registries.
