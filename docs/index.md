# What is TabulaFlow?

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize, or transform across databases, spreadsheets and other
local files, public datasets, and the web. Like a general-purpose coding agent,
it can also write code, work with files, run shell commands, and browse the web.

<div class="demo-gallery" id="demo-gallery">
  <div class="demo-gallery__tabs" role="tablist" aria-label="TabulaFlow demos">
    <button type="button" role="tab" id="demo-overview" aria-selected="true"
      data-title="From question to interactive result"
      data-description="Show a user entering a request, the agent working, the completed chart, and the Chart, Data, and Query views."
      data-type="Product demo · 20–30 seconds">Overview</button>
    <button type="button" role="tab" id="demo-spending" aria-selected="false" tabindex="-1"
      data-title="Compare spending by merchant"
      data-description="Show the prompt, query execution, and completed bar chart."
      data-type="Visualization workflow">Spending</button>
    <button type="button" role="tab" id="demo-model-evaluation" aria-selected="false" tabindex="-1"
      data-title="Evaluate model performance"
      data-description="Show the prompt, grouped evaluation results, and completed chart."
      data-type="Analysis workflow">Model evaluation</button>
    <button type="button" role="tab" id="demo-receipts" aria-selected="false" tabindex="-1"
      data-title="Extract data from receipts"
      data-description="Show the source images, extraction progress, and completed workspace table."
      data-type="Multimodal workflow">Receipts</button>
    <button type="button" role="tab" id="demo-multiple-sources" aria-selected="false" tabindex="-1"
      data-title="Combine multiple sources"
      data-description="Show both connections, the workspace join, and the final grouped result."
      data-type="Cross-source workflow">Multiple sources</button>
    <button type="button" role="tab" id="demo-web-dataset" aria-selected="false" tabindex="-1"
      data-title="Build a dataset from the web"
      data-description="Show parallel browsing, extraction, normalization, and the reusable table."
      data-type="Dataset construction workflow">Web dataset</button>
    <button type="button" role="tab" id="demo-maps" aria-selected="false" tabindex="-1"
      data-title="Map geographic boundaries"
      data-description="Show the prompt, rendered boundaries, and interactive tooltips."
      data-type="Geospatial workflow">Maps</button>
    <button type="button" role="tab" id="demo-relationships" aria-selected="false" tabindex="-1"
      data-title="Explore relationships"
      data-description="Show the prompt, graph construction, and interactive result."
      data-type="Graph workflow">Relationships</button>
  </div>
  <div class="demo-gallery__stage" role="tabpanel" aria-labelledby="demo-overview">
    <video class="demo-gallery__video" controls preload="none" hidden></video>
    <figure class="media-placeholder media-placeholder--video" aria-live="polite">
      <div class="media-placeholder__content">
        <span class="media-placeholder__type">Product demo · 20–30 seconds</span>
        <strong>From question to interactive result</strong>
        <span>Show a user entering a request, the agent working, the completed chart, and the Chart, Data, and Query views.</span>
      </div>
      <figcaption>Production placeholder · Include captions and a text transcript.</figcaption>
    </figure>
  </div>
</div>

## Get started

TabulaFlow requires Python 3.11 or later on macOS or Linux. Install it with
[`uv`](https://docs.astral.sh/uv/), set a model provider key, and launch it:

```bash
uv tool install tabulaflow
export OPENAI_API_KEY="your-api-key"
tabulaflow
```

TabulaFlow opens with bundled sample data, so you can start exploring
immediately.

[Connect your data](data-agent/connecting-data.md){ .inline-cta }
[Configuration](data-agent/configuration.md){ .inline-cta }

## What TabulaFlow can do

Consider TabulaFlow if you regularly analyze data in Jupyter notebooks, explore
databases with DBeaver or Neo4j Browser, work with Hugging Face datasets or
Wikidata, or conduct deep research with structured
datasets.

- **Interactive visualization.** Create charts, maps, and relationship graphs
  backed by queryable, parameterized data, including graphs from Neo4j.
  Watch [spending](#demo-spending), [model evaluation](#demo-model-evaluation),
  [maps](#demo-maps), or [relationships](#demo-relationships).
- **Multimodal data browsing.** Browse databases or Hugging Face datasets
  directly (no LLM needed). View images, PDFs, and other media directly inside
  tables, or ask an agent to analyze them.
  Watch [receipt extraction](#demo-receipts).
- **Cross-source analysis.** Combine files and databases in a local workspace
  without changing the original sources.
  Watch [multiple-source analysis](#demo-multiple-sources).
- **Large-scale dataset construction.** Combine multiple sources and turn
  unstructured web pages and documents into structured, normalized tables with
  thousands of rows for deep research.
  Watch [web dataset construction](#demo-web-dataset).
- **Agentic data enrichment.** Enrich each row with an agent that can browse
  the web, query connected databases, and return typed results. Process many
  rows concurrently.
  Watch [receipt extraction](#demo-receipts).
- **Parallel browser use.** TabulaFlow's browser harness lets agents interact
  with many web pages in parallel during complex deep research tasks, including
  pages that require clicks and forms.
  Watch [web dataset construction](#demo-web-dataset).

## Why TabulaFlow?

General-purpose coding agents (e.g., Claude Code) are powerful tools for
programming and simple data analysis. TabulaFlow is built on a
harness (see [How TabulaFlow is designed](#how-tabulaflow-is-designed)) that enables workflows such as
ambitious deep research and large-scale data enrichment. It also
provides a UI for browsing large tables and visualizing data.

Many AI database assistants (e.g., Chat2DB) focus on SQL generation for a
single database. TabulaFlow supports broader, general-purpose workflows across
relational and graph databases, local files, public datasets, and the web.

## How TabulaFlow is designed

Like a coding agent, TabulaFlow is an LLM that calls tools in a loop.
The main difference is that exiting coding agent harness are built around files and shell,
while TabulaFlow treats tables as first-class citizens, as its name suggests.
Our harness is designed to maximize agent and human ergonomics for data tasks, and
remains fully functional without filesystem or shell access.

The diagram below shows a simple chat-to-database workflow. You can register
data sources with `/connect`, or the agent can connect them through a tool call.
The agent runs queries to produce tables, attaches visualization specifications
to create visual artifacts (e.g., charts), and references one or more artifacts in
its answer.

<figure class="process-diagram">
  <div class="horizontal-flow" role="img" aria-label="The data connector registry contains SQLite, CSV, Hugging Face, and additional sources identified by aliases. The run_query tool counts orders by channel to create a result table, and render_chart creates a donut chart artifact using channel and order count.">
    <div class="flow-stage source-stage">
      <span class="flow-label">Data connector registry</span>
      <div class="connector-list" aria-hidden="true">
        <div class="connector-entry">
          <svg class="connector-icon" viewBox="0 0 24 24"><path d="M6 3.5h8l4 4v13H6z"></path><path d="M14 3.5v4h4M8.5 11h7M8.5 14.5h7M8.5 18h7M11 11v7"></path></svg>
          <span class="connector-copy"><strong>merchants</strong><code>project/merchants.csv</code></span>
        </div>
        <div class="connector-entry">
          <svg class="connector-icon" viewBox="0 0 24 24"><ellipse cx="12" cy="5.5" rx="7.5" ry="3"></ellipse><path d="M4.5 5.5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6"></path><path d="M4.5 11.5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6"></path></svg>
          <span class="connector-copy"><strong>orders</strong><code>sqlite:///orders.sqlite</code></span>
        </div>
        <div class="connector-entry">
          <svg class="connector-icon" viewBox="0 0 24 24"><circle cx="12" cy="9.5" r="5.5"></circle><path d="M9.5 9h.01M14.5 9h.01M9.5 12c1.4 1.3 3.6 1.3 5 0M7.3 14c-2.2-.8-4.3.3-5.3 2.3M16.7 14c2.2-.8 4.3.3 5.3 2.3M2 16.3l3.2 3M22 16.3l-3.2 3M5.2 19.3l2.6-2.1M18.8 19.3l-2.6-2.1"></path></svg>
          <span class="connector-copy"><strong>reviews</strong><code>https://huggingface.co/datasets/yelp</code></span>
        </div>
        <span class="connector-more">•••</span>
      </div>
    </div>
    <div class="flow-link flow-link--down">
      <span class="flow-arrow" aria-hidden="true"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M40 14V62H92"></path></svg></span>
      <div class="flow-call" aria-hidden="true">
        <svg class="agent-icon" viewBox="0 0 24 24"><path d="M12 4V2M9.5 2h5M7 7h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-6a3 3 0 0 1 3-3Z"></path><path d="M8.5 12h.01M15.5 12h.01M9 16h6"></path></svg>
        <code><strong>run_query</strong><span><span class="syntax-keyword">SELECT</span> channel,</span><span class="sql-line"><span class="syntax-function">COUNT</span>(*) <span class="syntax-keyword">AS</span> orders</span><span><span class="syntax-keyword">FROM</span> <span class="syntax-name">orders</span></span><span><span class="syntax-keyword">GROUP BY</span> channel</span></code>
      </div>
    </div>
    <div class="flow-stage table-stage">
      <span class="flow-label">Result table</span>
      <div class="table-preview" aria-hidden="true">
        <strong>channel</strong><strong>orders</strong>
        <span>Online</span><span>1,240</span>
        <span>In-store</span><span>860</span>
        <span>Partner</span><span>530</span>
      </div>
    </div>
    <div class="flow-link flow-link--up">
      <span class="flow-arrow" aria-hidden="true"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M8 62H60V14"></path></svg></span>
      <div class="flow-call" aria-hidden="true">
        <svg class="agent-icon" viewBox="0 0 24 24"><path d="M12 4V2M9.5 2h5M7 7h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-6a3 3 0 0 1 3-3Z"></path><path d="M8.5 12h.01M15.5 12h.01M9 16h6"></path></svg>
        <code><strong>render_chart</strong><span>{</span><span class="json-line"><span class="syntax-key">"mark"</span>: <span class="syntax-string">"arc"</span>,</span><span class="json-line"><span class="syntax-key">"theta"</span>: <span class="syntax-string">"orders"</span>,</span><span class="json-line"><span class="syntax-key">"color"</span>: <span class="syntax-string">"channel"</span></span><span>}</span></code>
      </div>
    </div>
    <div class="flow-stage chart-stage">
      <span class="flow-label">Artifact</span>
      <div class="artifact-chart" aria-hidden="true">
        <div class="donut-plot">
          <svg viewBox="0 0 42 42"><circle class="donut-track" cx="21" cy="21" r="16"></circle><circle class="donut-segment donut-segment--online" cx="21" cy="21" r="16" pathLength="100"></circle><circle class="donut-segment donut-segment--store" cx="21" cy="21" r="16" pathLength="100"></circle><circle class="donut-segment donut-segment--partner" cx="21" cy="21" r="16" pathLength="100"></circle><line class="donut-separator" x1="33.5" y1="21" x2="40.5" y2="21"></line><line class="donut-separator" x1="8.7" y1="23.3" x2="1.8" y2="24.5"></line><line class="donut-separator" x1="24.7" y1="9.1" x2="26.8" y2="2.4"></line></svg>
        </div>
        <div class="donut-legend"><span><i class="donut-swatch donut-swatch--online"></i>Online</span><span><i class="donut-swatch donut-swatch--store"></i>In-store</span><span><i class="donut-swatch donut-swatch--partner"></i>Partner</span></div>
      </div>
    </div>
  </div>
</figure>

This design has three benefits:

- **Agent ergonomics.** The agent writes only queries and
  visualization specifications. TabulaFlow handles the result data and rendering,
  so the agent never handcrafts data values or HTML to create
  visual artifacts.
- **Human ergonomics.** TabulaFlow tracks data provenance: each visualization
  exposes its underlying data table, and each table exposes the query that
  produced it. Our UI ensures a consistent look and efficient navigation.
- **Security.** The data agent remains fully functional for data work even when
  the shell tool is disabled.

Connected sources are read-only. When necessary, the agent can transform
tables in a local workspace and keep intermediate files in a temporary scratch
directory, so your source data and project directory remain unchanged by
default. You can ask the agent at any time to export results to local files in
any format you need for saving, sharing, or further use.

## Build and research with TabulaFlow

### Build with the Python library

Create your own data agents and applications with an async-native library
written in pure Python. Reuse its connectors, tools, and structured outputs
to build workflows tailored to your needs.
[Explore the library](python-library/quick-start.md){ .inline-cta }

### Run research experiments

Run large-scale experiments on text-to-SQL and text-to-Cypher benchmarks such
as Spider 2.0, CypherBench, and ARCS with TabulaFlow's research toolkit.
[Explore the toolkit](research-toolkit/quick-start.md){ .inline-cta }

!!! note "Public beta"
    TabulaFlow 0.1.0 is a public beta. Patch releases preserve documented
    public APIs; minor `0.x` releases may include documented breaking changes.
    We welcome your feedback.
