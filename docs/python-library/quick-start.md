# Quick start

Ask one agent about sales and customer support, then get a revenue chart and
a ticket table in one structured response. The example creates its own
in-memory databases; no database server or sample-data download is needed.

## Run the example

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) on macOS or
Linux. Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

This example makes paid model calls and sends the questions, schema, and
relevant query results to the provider.

From the repository root, run:

```bash
uv run python docs/examples/quick_start.py
```

This uses your checkout. No manual script creation is needed.

??? info "Run directly after publication"

    ```bash
    uv run https://megagonlabs.github.io/tabulaflow/examples/quick_start.py
    ```

    Once the documentation and pinned repository revision are public, uv can
    download the script and prepare its dependencies without a checkout.
    Review the code below before running it.

## The example

Load two in-memory databases, inspect the schema, then register them as
`sales` and `support`. The agent routes its queries and returns separate
chart and table artifacts; no join or workspace is needed.

[Download quick_start.py](../examples/quick_start.py){ download="quick_start.py" }

```python title="quick_start.py"
--8<-- "examples/quick_start.py"
```

Expect a chart showing **West: $2,000** and **East: $1,500**, plus a table of
tickets **201** and **202**. Labels and order may vary. The script prints the
output structure; it does not open a chart viewer.

In long-running applications, use `try/finally` so cleanup also runs on errors.

## Next steps

Once TabulaFlow is published, add it to your own project with `uv add tabulaflow`.

- [Working with data](working-with-data.md): connect your own sources.
- [Agents API](api/agents.md): explore tools and streaming with `run_stream()`.
- [Output API](api/output.md#resolving-outputs): resolve artifacts into data and chart specifications.
