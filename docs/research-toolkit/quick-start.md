# Quick start

TabulaFlow provides benchmark loaders, research agents, experiment pipelines,
and evaluation metrics for text-to-query research. Manage benchmark data with
the command line, then define experiments in version-controlled Python.

Choose the building blocks you need:

- [Benchmarks](benchmarks.md) load questions, reference queries, and database
  connectors through one async interface.
- [Experiment runs](running-experiments.md) keep prediction, execution,
  evaluation, usage, and reports together.
- [Research agents](research-agents.md) cover direct prompting, schema-aware
  methods, ambiguity-aware SQL, and dbt transformations.
- [Evaluation](evaluation.md) combines task metrics with run-level aggregation.

## Example: Evaluate a schema-linking agent

This example selects three BIRD-SQL development tasks, predicts SQL with the
schema-linking agent, executes each query, evaluates the results, and writes a
reusable experiment run.

```python title="research_quick_start.py"
--8<-- "examples/research_quick_start.py"
```

The script prints aggregate execution accuracy, executability, and prediction
success. It writes `result.json`, `result_summary.csv`, and readable per-task
reports under `runs/bird-schema-linking`. Exact predictions and scores can vary
between model calls.

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
script closes every database connector even if a stage fails.

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run python docs/examples/research_quick_start.py
    ```

    This uses your checkout rather than the installed package.

Next: [choose a benchmark](benchmarks.md), or learn how an
[experiment run](running-experiments.md) moves through each stage.
