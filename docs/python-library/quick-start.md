# Build with TabulaFlow

Build data agents with reusable connectors, tools, and structured outputs.
Use the components independently or combine them in a `ChatSession` to work
across multiple data sources. Connectors and outputs also work without an LLM.

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

Set your API key and run the complete example with
[uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uv init tabulaflow-examples
cd tabulaflow-examples
uv add tabulaflow
export OPENAI_API_KEY="your-api-key"
uv run tabulaflow examples run quick-start
```

This project and its environment can be reused for the other examples. For an example without
an API key, try [Data connectors](data-connectors.md).

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
