# Build with TabulaFlow

Build data agents with reusable connectors, tools, and structured outputs.
Use the components independently or combine them in a `ChatSession` to work
across multiple data sources. Connectors and outputs also work without an LLM.

## Example: Chat with two data sources

Connect two in-memory databases, ask one question across both, and inspect
the returned chart and table.

```python title="quick_start.py"
--8<-- "examples/quick_start.py:example"
```

Expect revenue of **West: $2,000** and **East: $1,500**, plus open high-priority
tickets **201** and **202**. `result.text` contains the answer; `result.output`
contains the chart and table specifications. See [Structured outputs](structured-outputs.md)
for parameter-driven outputs.

## Try it yourself

Set your API key and run the complete example with
[uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
export OPENAI_API_KEY="your-api-key"
uv run https://megagonlabs.github.io/tabulaflow/examples/quick_start.py
```

The script creates the sample databases, prints the answer and artifact data,
and closes its resources. It makes paid model calls; wording and artifact labels
may vary. For a local example without an API key, try [Data connectors](data-connectors.md).

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run python docs/examples/quick_start.py
    ```

    This uses your checkout instead of the script's pinned package version.

## Use in your project

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

- [Data connectors](data-connectors.md): query sources and inspect schemas.
- [Extraction and enrichment](extraction-and-enrichment.md): turn documents into records and enrich DataFrames.
- [Chat sessions](chat-sessions.md): add follow-up questions and streaming.
- [Structured outputs](structured-outputs.md): resolve tables, charts, maps, and graphs.
- [Custom agents](custom-agents.md): combine reusable tools with your own actions.
- [API reference](api-reference.md): look up types, configuration, and contracts.
