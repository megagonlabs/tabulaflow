# Build with TabulaFlow

We originally started TabulaFlow as an async-native Python library for building
and researching data agents. It provides reusable, typed building blocks for data
access, agent workflows, and structured outputs. A unified connector interface
handles backend-specific execution details, so you can focus on your agent's
logic.

Use the components together or choose the building blocks you need:

- [Data connectors](data-connectors.md): inspect schemas and query SQL
  databases, Neo4j, SPARQL endpoints, files, and datasets through a unified
  async interface.
- [Chat sessions](chat-sessions.md): use `ChatSession` to converse
  across multiple data sources, run tools, and stream answers and progress,
  with automatic context compaction for long conversations.
- [Structured outputs](structured-outputs.md): let agents produce tables, charts, maps,
  and graphs as structured artifacts, with optional lazy data resolution for
  parameter-driven interaction.
- [Agent tools](agent-tools.md): use query, visualization, and
  document-extraction tools in your own agent workflows without adopting
  `ChatSession`.
- [Schema and result formatting](api/output.md#formatting): turn structured
  schemas and query results into readable text for LLM prompts or human
  inspection.

These building blocks are organized into four layered packages:
`core <- data <- output <- agents`. See the
[API reference](api-reference.md) for how they fit together.

## Example: Chat with two data sources

This example connects two in-memory SQLite databases to a chat session to
compare revenue across regions and find open high-priority support tickets.
It then inspects the resulting table and chart. No database server or sample
files are needed.

```python title="quick_start.py"
--8<-- "examples/quick_start.py"
```

`result.text` contains the answer, and `result.output` describes the artifacts.
The output store provides their DataFrames and query metadata; chart artifacts
also carry a Vega-Lite specification.

Expect a chart showing **West: $2,000** and **East: $1,500**, plus a table of
tickets **201** and **202**. Labels and order may vary. The script prints the
data and Vega-Lite specification; it does not open a chart viewer.

In long-running applications, use `try/finally` so cleanup also runs on errors.

## Try it yourself

To try TabulaFlow without an API key, start with the
[Data connectors](data-connectors.md#example-find-products-to-restock) or
[Structured outputs](structured-outputs.md#example-switch-between-revenue-and-profit)
example. Both run locally without model calls.

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) on macOS or
Linux. Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

This example makes paid model calls and sends the questions, schema, and
relevant query results to the provider.

Run the example directly:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/quick_start.py
```

uv downloads the script and prepares Python and its dependencies. No project
setup or manual file creation is needed.

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run python docs/examples/quick_start.py
    ```

    This uses your checkout instead of the script's pinned package version.

## Use in your project

To use TabulaFlow as a library in your own project:

=== "uv"

    ```bash
    uv add tabulaflow
    ```

=== "pip"

    ```bash
    pip install tabulaflow
    ```

- [Data connectors](data-connectors.md): connect sources and query them directly.
- [Chat sessions](chat-sessions.md): add follow-up questions and streaming.
- [Structured outputs](structured-outputs.md): work with data and interactive artifacts.
- [Agent tools](agent-tools.md): reuse tools and add your own agent behavior.
