# Quick start

TabulaFlow Research extends the main Python library for AI researchers working
on text-to-SQL and data agents. Its main building blocks include benchmark
loaders, research agents, evaluation metrics, and experiment pipelines. It is
designed around principles that enable flexible, rapid, and transparent
experiments:

- **Benchmark-ready.** Run BIRD-SQL, Spider 2.0, Beaver, ARCS, AMBROSIA-S, and
  CypherBench with managed setup and official leaderboard metrics.
- **Transparent and fully typed.** Work with typed tasks, schemas, and
  predictions rather than black-box dictionaries or schema strings. Write
  Python instead of YAML.
- **Async-native for large-scale concurrency.** Task inference, LLM calls, and
  database queries are async and parallelizable, with configurable concurrency
  controls that can make full use of provider limits.
- **Modular and extensible.** Use any building blocks you need, or extend them by
  implementing their public protocols.
- **Built-in tracking.** Record trajectories, token usage, and latency for
  analysis, with optional Langfuse and Phoenix tracing.
- **Simple and performant agents.** Simple yet state-of-the-art agent
  implementations provide a performant starting point.

## Example: Build and evaluate a custom agent

This example builds a typed plan-and-query agent from TabulaFlow's model,
schema, task, tracking, and result primitives. The agent selects relevant tables
and predicts SQL, then the research pipeline runs it on three BIRD-SQL tasks,
executes the queries, evaluates the results, and writes a reusable experiment
run.

```python title="research_quick_start.py"
--8<-- "examples/research_quick_start.py"
```

`PlanAndQueryAgent` is an ordinary Python class that implements the simple task
contract; it does not modify or fork TabulaFlow. Its structured model output
keeps the selected tables available for analysis, while `SimpleNL2QTaskOutput`
records the predicted query and intermediate data.

The script prints a benchmark question, structured schema tables, the custom
table selection, predicted SQL, query result, and aggregate metric. It shows how
method-specific data remains available beside the prediction and how query
results arrive as DataFrames—without parsing nested dictionaries or text.

Exact predictions and scores can vary between model calls.

To keep the complete run, including structured JSON, a CSV summary, and
readable per-task reports, add:

```python
result.to_directory("runs/plan-and-query")
```

The quick-start script does not write to your project by default.

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

- [Benchmarks](benchmarks.md) load questions, reference queries, and database
  connectors through one async interface.
- [Experiment runs](running-experiments.md) keep prediction, execution,
  evaluation, usage, and reports together.
- [Research agents](research-agents.md) cover direct prompting, schema-aware
  methods, ambiguity-aware SQL, and dbt transformations.
- [Evaluation](evaluation.md) combines task metrics with run-level aggregation.
