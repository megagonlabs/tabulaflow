# Quick start

TabulaFlow's research toolkit lets you run, compare, and develop text-to-query
methods in Python. It provides benchmark loaders, built-in agents, execution
and evaluation stages, and typed results with usage and trajectories.

## How an experiment fits together

```text
Load benchmark → Predict → Execute → Evaluate → Save and analyze
```

A **benchmark loader** returns an `NL2QDataset`: selected tasks and live database
connectors. Each **task** contains a question and its reference answer. An
**agent** predicts an output for each task; `predict_async(...)` collects those
outputs and their usage into an `NL2QRunResult`. Execution attaches query
results, and evaluation adds task scores and run-level aggregates.

The task family determines which agents and metrics can work together:

| Task family | Agent output | Example benchmarks |
| --- | --- | --- |
| Query (`simple`) | One SQL or Cypher query | BIRD-SQL, Spider 2.0 Snow/Lite, Beaver, CypherBench |
| Ambiguous query (`ambig`) | An intended query, flat interpretations, or structured ambiguity points | ARCS, AMBROSIA-S |
| Transformation (`dbt`) | A modified dbt project | Spider 2.0 dbt |

`simple` names the single-query contract; it does not describe task difficulty.
The toolkit reuses the Python library's connectors, schemas, and model runtime.

## Example: Evaluate a full-schema agent

This example loads three BIRD-SQL tasks and runs a full-schema agent on them
concurrently. The agent receives the complete database schema and can execute
queries while working. The pipeline then populates any missing execution
results and evaluates BIRD-SQL execution accuracy.

```python title="research_quick_start.py"
--8<-- "examples/research_quick_start.py"
```

The script prints a benchmark question, predicted SQL, its DataFrame result,
and aggregate accuracy. Tasks, predictions, execution results, and metrics
remain structured and directly accessible throughout the experiment.

Exact predictions and scores can vary between model calls.

The script keeps its result in memory. See
[saving a run](running-experiments.md#save-a-run) to write structured JSON, a
CSV summary, and readable task reports.

## Try it yourself

Install TabulaFlow in a new or existing project:

=== "uv"

    ```bash
    uv add tabulaflow
    ```

=== "pip"

    ```bash
    pip install tabulaflow
    ```

Download BIRD-SQL and set an OpenAI API key:

```bash
uv run tabulaflow benchmark download bird-sql
export OPENAI_API_KEY="your-api-key"
```

Then save the example in your project and run:

```bash
uv run python research_quick_start.py
```

This makes paid model calls and sends benchmark questions, relevant schema, and
tool results to the configured provider. BIRD-SQL is downloaded locally. The
script closes its database connectors before exiting.

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run python docs/examples/research_quick_start.py
    ```

    This uses your checkout rather than the installed package.

## Explore the toolkit

- [Benchmarks](benchmarks.md): choose, install, and load benchmark tasks.
- [Agents](agents.md): choose and configure a built-in method.
- [Running experiments](running-experiments.md): scale, save, and compare runs.
- [Evaluation and analysis](evaluation.md): choose metrics and inspect results.
- [Extending the toolkit](extending.md): implement and evaluate your own method.
- [API reference](api-reference.md): look up contracts, fields, and signatures.
