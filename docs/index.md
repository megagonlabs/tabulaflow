# What is TabulaFlow?

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize or transform across databases, spreadsheets and other
local files, public datasets, and the web. Like a general-purpose coding agent,
it can also write code, work with files, run shell commands, and browse the web
interactively.

<figure class="media-placeholder media-placeholder--video" aria-label="Placeholder for the TabulaFlow product demo video">
  <div class="media-placeholder__content">
    <span class="media-placeholder__type">Video · 16:9 · 20–30 seconds</span>
    <strong>From question to interactive result</strong>
    <span>Show a user entering a request, the agent working, the completed chart, and the Chart, Data, and Query views.</span>
  </div>
  <figcaption>Production placeholder · Include captions and a text transcript.</figcaption>
</figure>

## How is TabulaFlow different?

General-purpose coding agents (e.g., Claude Code) are built around files, but
TabulaFlow treats tables as first-class citizens, as its name suggests. We
design TabulaFlow around a table-native agent harness for tasks that existing
agents are not built to handle.

Many database-focused data agents (e.g., Chat2DB) focus on SQL generation.
TabulaFlow supports broader workflows across relational and graph databases,
local files, public datasets, and the web.

- **Interactive visualization.** Create charts, maps, and relationship graphs
  backed by queryable, parameterized data, including graphs from Neo4j.
- **Multimodal data browsing.** Browse images and PDFs directly inside tables,
  or ask an agent to analyze them alongside the other data.
- **Large-scale dataset construction.** Combine multiple sources and turn
  unstructured web pages and documents into structured, normalized tables with
  thousands of rows.
- **Parallel semantic operations.** Enrich tables with new columns by
  coordinating thousands of row-wise subagents in parallel.
- **Parallel browser use.** TabulaFlow's browser harness lets agents interact
  with many web pages in parallel, including pages that require clicks and
  forms.
- **Customization.** TabulaFlow's core is written in pure Python. Build your
  own data application with components at any level, from data connectors to
  agent tools.

## Build and research with TabulaFlow

### Python Library

We build TabulaFlow not only as an end-user application but also as a Python
library with clean, minimal building blocks for modern data agents, from data
connectors to agent tools. You can use them to create agents and applications
tailored to your needs. [Explore the library →](python-library/index.md)

### Research Toolkit

TabulaFlow also includes a research toolkit for rapid, large-scale
experimentation on text-to-SQL and text-to-Cypher benchmarks such as Spider
2.0, CypherBench, and ARCS. [Explore the toolkit →](research-toolkit/index.md)

## How TabulaFlow handles your data

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
