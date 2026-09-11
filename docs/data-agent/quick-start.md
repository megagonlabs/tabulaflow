# Quick start

Install the Data Agent and complete a first workflow with its bundled sample
data. The setup takes only a few minutes.

## 1. Install TabulaFlow

TabulaFlow requires Python 3.11 or later and supports macOS and Linux.
[`uv`](https://docs.astral.sh/uv/) is recommended because it installs the
command in an isolated environment.

=== "uv (recommended)"

    ```bash
    uv tool install tabulaflow
    ```

=== "pip"

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install tabulaflow
    ```

Install Chromium if you want the agent to browse the web:

=== "uv"

    ```bash
    uv tool run --from playwright playwright install chromium
    ```

=== "pip"

    ```bash
    playwright install chromium
    ```

The browser runtime is optional. Database queries, local file analysis, and
other workflows do not require it.

## 2. Configure a model provider

Set a key for OpenAI or Anthropic in the shell where you will launch
TabulaFlow:

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"
    ```

When no model preference has been saved, TabulaFlow selects a balanced preset
from the credentials it detects. Use `/config` inside the app to choose a
different preset or disable the LLM.

Without a supported key, the app still starts and lets you connect and inspect
data, but conversational analysis remains unavailable.

## 3. Launch in your project

Run TabulaFlow from the directory where it should work:

```bash
cd /path/to/your/project
tabulaflow
```

Relative file paths and file-tool operations resolve from this directory. The
Data Agent can also run shell commands there, so use a trusted project and
review requests before giving it access to sensitive credentials or files.

## 4. Run the sample workflow

When no user source is connected, TabulaFlow automatically connects a small
sample database. Ask:

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

The agent inspects the sample schema, computes the result, and opens an
interactive chart with the underlying rows and query available behind it.

<figure class="media-placeholder media-placeholder--screenshot" aria-label="Placeholder for an annotated screenshot of the completed sample workflow">
  <div class="media-placeholder__content">
    <span class="media-placeholder__type">Annotated screenshot · 16:10</span>
    <strong>Your first completed workflow</strong>
    <span>Show the spending chart in the output pane and identify the Chart, Data, and Query views.</span>
  </div>
  <figcaption>Production placeholder · Supply concise alt text for the final image.</figcaption>
</figure>

## Next steps

- Browse [Examples](examples.md) for more analysis, extraction, map, and graph
  workflows.
- Use [Connecting data](connecting-data.md) to add a file, database, or public
  dataset.
- Open [Configuration](configuration.md) to select models and tune runtime
  behavior.
- See [Troubleshooting](../reference/troubleshooting.md) if installation,
  credentials, or browser startup fails.
