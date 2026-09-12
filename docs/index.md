# What is TabulaFlow?

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize, or transform across databases, spreadsheets and other
local files, public datasets, and the web. Like a general-purpose coding agent,
it can also write code, work with files, run shell commands, and browse the web.

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
- **Multimodal data browsing.** Browse databases or Hugging Face datasets
  directly (no LLM needed). View images, PDFs, and other media directly inside
  tables, or ask an agent to analyze them.
- **Large-scale dataset construction.** Combine multiple sources and turn
  unstructured web pages and documents into structured, normalized tables with
  thousands of rows.
- **Parallel semantic operations.** Enrich tables with new columns by
  coordinating thousands of row-wise subagents in parallel to collect
  information, classify records, and annotate data.
- **Parallel browser use.** TabulaFlow's browser harness lets agents interact
  with many web pages in parallel during complex deep research tasks, including
  pages that require clicks and forms.
- **Async-native Python library.** The core of TabulaFlow is a library written
  in pure Python. Build your own data application with components at any level,
  from data connectors to agent tools.

## Build and research with TabulaFlow

### Python Library

We build TabulaFlow not only as an end-user application but also as an
async-native Python library with clean, minimal building blocks for modern data
agents, from data connectors to agent tools. You can use them to create agents
and applications tailored to your needs.
[Explore the library →](python-library/index.md)

### Research Toolkit

TabulaFlow also includes a research toolkit for rapid, large-scale
experimentation on text-to-SQL and text-to-Cypher benchmarks such as Spider
2.0, CypherBench, and ARCS. [Explore the toolkit →](research-toolkit/index.md)

## How does TabulaFlow work?

The diagram below shows how TabulaFlow works, using SQLite as an example. You
can connect the database with `/connect`, or the agent can connect it through a
tool call. TabulaFlow registers the connection under an alias and makes the
schema available to the agent. The agent can then execute queries, save
intermediate results to a local workspace for further processing, and
attach visualization specifications to render charts, maps, and graphs.
This enables a fully in-memory agentic data workflow without exposing a shell
tool when security matters.

<figure class="process-diagram">
  <div class="horizontal-flow" role="img" aria-label="The command /connect merchants.sqlite adds a SQLite database to the data connector registry. The run_query tool executes SELECT * FROM merchant_totals to create a result table, and render_chart creates a bar chart artifact using merchant and total.">
    <div class="flow-link">
      <code><span>/connect</span><span>merchants.sqlite</span></code>
      <span class="flow-arrow" aria-hidden="true"></span>
    </div>
    <div class="flow-stage source-stage">
      <span class="flow-label"><span>Data connector</span><span>registry</span></span>
      <div class="source-symbol" aria-hidden="true"></div>
      <div class="source-copy">
        <strong>merchants.sqlite</strong>
        <code>alias: merchants</code>
      </div>
    </div>
    <div class="flow-link">
      <code><span>run_query(</span><span>SELECT * FROM</span><span>merchant_totals)</span></code>
      <span class="flow-arrow" aria-hidden="true"></span>
    </div>
    <div class="flow-stage table-stage">
      <span class="flow-label">Result table</span>
      <div class="table-preview" aria-hidden="true">
        <strong>merchant</strong><strong>total</strong>
        <span>Acme Market</span><span>$1,240</span>
        <span>City Cafe</span><span>$860</span>
      </div>
    </div>
    <div class="flow-link">
      <code><span>render_chart(</span><span>mark: bar</span><span>x: merchant</span><span>y: total)</span></code>
      <span class="flow-arrow" aria-hidden="true"></span>
    </div>
    <div class="flow-stage chart-stage">
      <span class="flow-label">Artifact</span>
      <div class="artifact-chart" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
      <span class="artifact-caption">Interactive result</span>
    </div>
  </div>
  <figcaption>From a database connection to an interactive result.</figcaption>
</figure>

Connected sources are read-only. To complete a task, the agent can transform
tables in a local workspace and keep intermediate files in a temporary scratch
directory, so your source data and project directory remain unchanged by
default. To export results to local files, simply ask the agent in natural
language.

!!! note "Public beta"
    TabulaFlow 0.1.0 is a public beta. Patch releases preserve documented
    public APIs; minor `0.x` releases may include documented breaking changes.
    We welcome your feedback.
