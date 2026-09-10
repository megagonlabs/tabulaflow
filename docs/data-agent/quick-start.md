# Quick start

## 1. Configure a model provider

Set an OpenAI or Anthropic API key:

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"
    ```

TabulaFlow automatically selects a model preset from the credentials that are
available. Without a supported key, it starts with the LLM disabled.

## 2. Launch in your project

```bash
cd /path/to/your/project
tabulaflow
```

The working directory defines where the agent's file and shell tools operate.
Run TabulaFlow only in a trusted environment.

## 3. Try the sample data

The installation includes a small sample database. Ask:

```text
Using the sample data, show the five merchants with the highest total spend
as a bar chart.
```

Use `/config` to select a different model preset and `/connect` to add your own
data. Next, see [Connecting data](connecting-data.md).
