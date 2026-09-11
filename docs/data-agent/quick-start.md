# Quick start

Install the Data Agent, then try your first workflow with the bundled sample
data.

## 1. Install TabulaFlow

TabulaFlow requires Python 3.11 or later and supports macOS and Linux. We
recommend [`uv`](https://docs.astral.sh/uv/) because it keeps the command in an
isolated environment.

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

Skip this step if you do not need web browsing. Database and local-file
workflows do not use Chromium.

## 2. Configure a model provider

Set an OpenAI or Anthropic key in the shell where you will launch TabulaFlow:

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"
    ```

TabulaFlow uses a balanced preset for the first provider it detects. Run
`/config` in the app to choose another preset or turn the LLM off.

Without a key, you can still connect and inspect data, but you cannot use
conversational analysis.

## 3. Launch in your project

Open the project directory where you want TabulaFlow to work:

```bash
cd /path/to/your/project
tabulaflow
```

TabulaFlow resolves relative paths from this directory and can run shell
commands there. Use a trusted project and least-privilege credentials.

## 4. Run the sample workflow

TabulaFlow connects a small sample database when you have not added a source.
Ask:

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

The result opens as an interactive chart. You can also inspect its data and
query.

<figure class="media-placeholder media-placeholder--screenshot" aria-label="Placeholder for an annotated screenshot of the completed sample workflow">
  <div class="media-placeholder__content">
    <span class="media-placeholder__type">Annotated screenshot · 16:10</span>
    <strong>Your first completed workflow</strong>
    <span>Show the spending chart in the output pane and identify the Chart, Data, and Query views.</span>
  </div>
  <figcaption>Production placeholder · Supply concise alt text for the final image.</figcaption>
</figure>

## Next steps

- Try more analysis, extraction, map, and graph workflows in
  [Examples](examples.md).
- [Connect your data](connecting-data.md) from a file, database, or public
  dataset.
- Use [Configuration](configuration.md) to select a model or tune the runtime.
