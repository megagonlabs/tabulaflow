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
  [View example](data-agent/examples/compare-spending.md){ .inline-cta }
- **Multimodal data browsing.** Browse databases or Hugging Face datasets
  directly (no LLM needed). View images, PDFs, and other media directly inside
  tables, or ask an agent to analyze them.
  [View example](data-agent/examples/extract-receipts.md){ .inline-cta }
- **Large-scale dataset construction.** Combine multiple sources and turn
  unstructured web pages and documents into structured, normalized tables with
  thousands of rows.
  [View example](data-agent/examples/build-web-dataset.md){ .inline-cta }
- **Parallel semantic operations.** Enrich tables with new columns by
  coordinating thousands of row-wise subagents in parallel to collect
  information, classify records, and annotate data.
  [View example](data-agent/examples/extract-receipts.md){ .inline-cta }
- **Parallel browser use.** TabulaFlow's browser harness lets agents interact
  with many web pages in parallel during complex deep research tasks, including
  pages that require clicks and forms.
  [View example](data-agent/examples/build-web-dataset.md){ .inline-cta }
- **Async-native Python library.** The core of TabulaFlow is a library written
  in pure Python. Build your own data application with components at any level,
  from data connectors to agent tools.
  [View example](python-library/quick-start.md){ .inline-cta }

## Build and research with TabulaFlow

### Python Library

We build TabulaFlow not only as an end-user application but also as an
async-native Python library with clean, minimal building blocks for modern data
agents, from data connectors to agent tools. You can use them to create agents
and applications tailored to your needs.
[Explore the library](python-library/quick-start.md){ .inline-cta }

### Research Toolkit

TabulaFlow also includes a research toolkit for rapid, large-scale
experimentation on text-to-SQL and text-to-Cypher benchmarks such as Spider
2.0, CypherBench, and ARCS.
[Explore the toolkit](research-toolkit/index.md){ .inline-cta }

## How does TabulaFlow work?

Just like any coding agent, TabulaFlow is simply an LLM that calls a set of
tools in a loop. The diagram below shows how TabulaFlow works in a simple
chat-to-database scenario. You can connect a database with `/connect`, or the
agent can connect it through a tool call. TabulaFlow registers the connection
under an alias and constructs the schema so the agent can understand the
database structure. The agent can then execute queries to derive tables and
attach visualization specifications to render charts, maps, and graphs.
Finally, the agent presents one or multiple tables or visualization artifacts
to the user by referencing their IDs.
This enables a fully in-memory agentic data workflow without exposing a shell
tool when security matters.

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

Connected sources are read-only. When necessary, the agent can transform
tables in a local workspace and keep intermediate files in a temporary scratch
directory, so your source data and project directory remain unchanged by
default. To export results to local files, simply ask the agent in natural
language.

!!! note "Public beta"
    TabulaFlow 0.1.0 is a public beta. Patch releases preserve documented
    public APIs; minor `0.x` releases may include documented breaking changes.
    We welcome your feedback.
