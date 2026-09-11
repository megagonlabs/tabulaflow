# What is TabulaFlow?

Turn questions into data workflows.

TabulaFlow is an open-source data agent, Python library, and text-to-query
research toolkit. Connect databases, files, public datasets, and the web; then
analyze, transform, and present the results through one conversational
workflow.

[Get started](data-agent/quick-start.md) ·
[View on GitHub](https://github.com/megagonlabs/tabulaflow)

```bash
uv tool install tabulaflow
```

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

The primary experience. Launch TabulaFlow in a project directory and ask it to
connect sources, inspect schemas, run analyses, build datasets, and present
results as interactive tables, charts, maps, and graphs.

[Launch your first workflow →](data-agent/quick-start.md)

### Python Library

Build custom data applications with reusable connectors, agents, tools, and
structured output primitives.

[Explore the library →](python-library/index.md)

### Research Toolkit

Build and evaluate text-to-query agents against established SQL and graph-query
benchmarks.

[Explore the toolkit →](research-toolkit/index.md)

## What the Data Agent can do

- Query SQL databases, Neo4j graphs, SPARQL endpoints, and local files.
- Inspect schemas and representative values before composing an analysis.
- Combine data from separate sources in a writable local workspace.
- Gather and structure records from web pages, documents, images, and PDFs.
- Apply semantic operations such as classification, extraction, and entity
  matching across many rows.
- Present results as interactive tables, charts, maps, and graphs.

See [Examples](data-agent/examples.md) for complete prompts covering these
workflows.

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

Prompts and relevant tool results may be sent to your configured model
provider. TabulaFlow sends no telemetry to Megagon Labs. Review
[Security and privacy](reference/security-and-privacy.md) before working with
sensitive data.

!!! warning "Trusted local agent"
    TabulaFlow is not a sandbox. File, shell, browser, and data tools run with
    your user permissions. Launch it only in environments you trust and use
    least-privilege credentials.

!!! note "Public beta"
    TabulaFlow 0.1.0 is a public beta. Patch releases preserve documented
    public APIs; minor `0.x` releases may include documented breaking changes.
