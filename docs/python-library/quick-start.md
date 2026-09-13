# Quick start

Build a chat agent over your data and get structured results your application
can inspect and render.

## Chat with two data sources

Compare revenue across regions and find open high-priority support tickets.
This example creates two small SQLite databases in memory, so you don't need
a database server or sample files.

[Download quick_start.py](../examples/quick_start.py){ download="quick_start.py" }

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
