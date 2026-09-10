# TabulaFlow

Turn questions into data workflows.

TabulaFlow is an open-source project for analyzing, transforming, and
visualizing data from databases, files, public datasets, and the web.

[Get started](data-agent/quick-start.md) · [View on GitHub](https://github.com/megagonlabs/tabulaflow)

```bash
uv tool install tabulaflow
```

## Data Agent

Connect sources, explore schemas, run analyses, build datasets, and present
results as tables, charts, maps, and graphs.

[Launch your first workflow →](data-agent/quick-start.md)

## Python Library

Build custom data applications with reusable connectors, agents, tools, and
structured output primitives.

[Explore the library →](python-library/index.md)

## Research Toolkit

Build and evaluate text-to-query agents against established SQL and graph
query benchmarks.

[Explore the toolkit →](research-toolkit/index.md)

## One workspace, many kinds of data

TabulaFlow works with SQL databases, Neo4j graphs, SPARQL endpoints, local
files, Hugging Face datasets, and web content. It can combine derived data in a
local DuckDB workspace and turn the result into an interactive artifact.

```text
Using the sample data, show the five merchants with the highest total spend
as a bar chart.
```

!!! note "Public beta"
    TabulaFlow 0.1.0 is a public beta. Patch releases preserve documented
    public APIs; minor `0.x` releases may include documented breaking changes.
