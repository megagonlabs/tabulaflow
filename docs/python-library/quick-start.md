# Build with TabulaFlow

At the core of TabulaFlow is a minimalist, async-native Python library for building
and researching data agents. It was the first thing we built when we started this project because existing libraries
lacked the abstractions we needed. Its building blocks allow you to write agent
logic that runs across different database backends and research benchmarks. The same library
powers the [TabulaFlow data agent](../index.md).

You can use any of these building blocks to create
data applications with (e.g. data agents) or without an LLM (e.g., interactive dashboards). Choose the
building blocks you need:

- [Data connectors](data-connectors.md): inspect schemas and query SQL
  databases, Neo4j, SPARQL endpoints, files, and datasets through a unified
  async interface.
- [Extraction and enrichment](extraction-and-enrichment.md): turn documents
  into structured records and enrich DataFrames with new fields.
- [Chat sessions](chat-sessions.md): use `ChatSession` to converse
  across multiple data sources, run tools, and stream answers and progress,
  with automatic context compaction for long conversations.
- [Structured outputs](structured-outputs.md): let agents produce tables, charts, maps,
  and graphs as structured artifacts by defining declarative specifications, with optional lazy data resolution for
  parameter-driven interaction.
- [Custom agents](custom-agents.md): combine reusable query, visualization, and
  document tools with your own functions and actions, without adopting `ChatSession`.
- [Schema and result formatting](api/output.md#formatting): turn structured
  schemas and query results into readable text for LLM prompts or human
  inspection.

These building blocks are fully typed and organized into four layers:
`core <- data <- output <- agents`. See the
[API reference](api-reference.md) for how they fit together.

## Example: Chat with two data sources

Sales and support records live in separate databases. Compare revenue by
region and find open high-priority tickets in one request, with an inspectable
chart and table.

```python title="quick_start.py"
--8<-- "tabulaflow/examples/quick_start.py:example"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-quick-start.txt"
    ```

`result.text` contains the answer; `result.output` contains the chart and table
specifications. See [Structured outputs](structured-outputs.md) for
parameter-driven outputs.

## Try it yourself

Install TabulaFlow once with [`uv`](https://docs.astral.sh/uv/), set your API
key, and run the bundled example:

```bash
uv tool install tabulaflow
export OPENAI_API_KEY="your-api-key"
tabulaflow examples run quick-start
```

The tool installation can run every bundled example from any directory. For an
example without an API key, try [Data connectors](data-connectors.md).

## Build in your project

Install TabulaFlow in a Python project when you are ready to import it in your
own code:

=== "uv"

    ```bash
    uv add tabulaflow
    ```

=== "pip"

    ```bash
    pip install tabulaflow
    ```

The default installation includes the complete dependency set for the Python
library and the `tabulaflow` data-agent application (Chromium is installed
separately when web browsing is needed). Advanced library users who manage
their own dependencies can instead run `uv pip install --no-deps tabulaflow` or
`pip install --no-deps tabulaflow`, then install the packages required by the
APIs and connectors they use.
