# Quick start

TabulaFlow is an async-native Python library for building data agents and
applications. Use its connectors, tools, and structured outputs together, or
bring individual components into your own workflows.

Choose the building blocks you need:

- [Data connectors](api/data.md): inspect structured schemas and query SQL
  databases, Neo4j, SPARQL endpoints, files, and datasets through a unified
  async interface.
- [Source registry](api/data.md#connector-registry): give connectors names with
  `DataConnectorRegistry`, so an agent can select the appropriate source for
  each query.
- [Chat sessions](api/agents.md#chat-sessions): use `ChatSession` to maintain a
  conversation, run tools, and stream answers and progress.
- [Structured outputs](api/output.md): let agents produce tables, charts, maps,
  and graphs as structured artifacts, with access to the underlying data and
  support for parameter-driven interactive outputs.
- [Reusable tools](api/agents.md#tool-contracts): use query, visualization, and
  document-extraction tools in your own agent workflows without adopting
  `ChatSession`.

These building blocks span four packages: `core <- data <- output <- agents`.
Each layer can depend on those to its left; see
[Concepts](concepts.md#how-the-layers-fit) for the architecture.

## Chat with two data sources

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

## Build with TabulaFlow

To use TabulaFlow in your own project:

=== "uv"

    ```bash
    uv add tabulaflow
    ```

=== "pip"

    ```bash
    pip install tabulaflow
    ```

- [Data API](api/data.md): connect your own sources.
- [Agents API](api/agents.md): explore tools and streaming with `run_stream()`.
- [Output API](api/output.md#resolving-outputs): resolve artifacts into data and chart specifications.
