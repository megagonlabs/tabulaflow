# What is TabulaFlow?

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, transform, or visualize across databases, spreadsheets and other
local files, public datasets, and the web.

General-purpose coding agents are built around files, but TabulaFlow treats
tables as first-class citizens, as its name suggests. We design its table-native
agent harness for tasks that existing agents are not built to handle. It can
construct structured, normalized datasets with thousands of rows through deep
research across web pages, enrich tables with new columns by coordinating
thousands of row-wise subagents in parallel, and create interactive visual
artifacts such as charts and maps.

We build TabulaFlow not only as an end-user application but also as a Python
library with clean, minimal building blocks for modern data agents, from data
connectors to agent tools. You can use them to create agents and applications
tailored to your needs.
TabulaFlow also includes a research toolkit for running experiments and
evaluating results on text-to-query benchmarks such as Spider 2.0.

<figure class="media-placeholder media-placeholder--video" aria-label="Placeholder for the TabulaFlow product demo video">
  <div class="media-placeholder__content">
    <span class="media-placeholder__type">Video · 16:9 · 20–30 seconds</span>
    <strong>From question to interactive result</strong>
    <span>Show a user entering a request, the agent working, the completed chart, and the Chart, Data, and Query views.</span>
  </div>
  <figcaption>Production placeholder · Include captions and a text transcript.</figcaption>
</figure>

## Choose how you use TabulaFlow

### Data Agent

Launch TabulaFlow in your project and ask it to explore data, run analyses,
build datasets, or create interactive results.

[Launch your first workflow →](data-agent/quick-start.md)

### Python Library

Build your own data applications with reusable connectors, agents, tools, and
output components.

[Explore the library →](python-library/index.md)

### Research Toolkit

Build and evaluate text-to-query agents on established SQL and graph-query
benchmarks.

[Explore the toolkit →](research-toolkit/index.md)

## What the Data Agent can do

- Query SQL databases, Neo4j graphs, SPARQL endpoints, and local files.
- Inspect schemas and representative values before running an analysis.
- Combine data from separate sources in a writable local workspace.
- Gather and structure records from web pages, documents, images, and PDFs.
- Apply semantic operations such as classification, extraction, and entity
  matching across many rows.
- Present results as interactive tables, charts, maps, and graphs.

See [Examples](data-agent/examples.md) for prompts you can try or adapt.

## How data flows

Connected sources remain read-only, while derived and combined data is written
to a session-local DuckDB workspace.

<figure class="media-placeholder media-placeholder--diagram" aria-label="Placeholder for a diagram explaining how data flows through TabulaFlow">
  <div class="media-placeholder__content">
    <span class="media-placeholder__type">Diagram · wide</span>
    <strong>How data flows through TabulaFlow</strong>
    <span>Show the user request entering the Data Agent, read-only connections to external sources, writes to the local workspace, optional model-provider context, and table, chart, map, or graph outputs.</span>
  </div>
  <figcaption>Production placeholder · Provide an equivalent text description.</figcaption>
</figure>

TabulaFlow may send prompts and relevant tool results to your model provider.
It sends no telemetry to Megagon Labs. Review [Security and
privacy](reference/security-and-privacy.md) before using sensitive data.

!!! warning "Trusted local agent"
    TabulaFlow is not a sandbox. File, shell, browser, and data tools run with
    your user permissions. Launch it only in environments you trust and use
    least-privilege credentials.

!!! note "Public beta"
    TabulaFlow 0.1.0 is a public beta. Patch releases preserve documented
    public APIs; minor `0.x` releases may include documented breaking changes.
