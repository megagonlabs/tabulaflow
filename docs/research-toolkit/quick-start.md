# Quick start

The tabulaflow research package is an extension library over
   its main python library for
   AI researchers who work on text-to-SQL / text-to-Cypher. Its main building blocks include benchmark
   loaders, research agents evaluation metrics, and experiment pipelines. We design it based on principles that
   enable flexible, rapid and transparent experiments:


- **Benchmark-ready.** Run BIRD-SQL, Spider 2.0, Beaver, ARCS, AMBROSIA-S, and
  CypherBench with managed setup and official leaderboard metrics.
- **Transparent and fully typed.**  Work with typed tasks, schemas, predictions rather than
  black-box dictionaries or schema strings. Write Python intead of YAML.
- **Async-native for large-scale concurrency.** Task inference, llm calls, database queries are all async and parallelizable with configuration concureency control that can exploit the provider limit.
- **Modular and extensible.** Use any building blocks you need, or extend by implementing their public protocols.
- **Built-in tracking.** Record trajectories, token usage, latency for analysis, with optional Langfuse and Phoenix tracing.
- **Simple and performant agents.** Simple yet state of the art agent implementations as your starting point. 

## Example: Evaluate a schema-linking agent

This example selects three BIRD-SQL development tasks, predicts SQL with the
schema-linking agent, executes each query, evaluates the results, and writes a
reusable experiment run.

```python title="research_quick_start.py"
--8<-- "examples/research_quick_start.py"
```

The script prints a concise summary with aggregate execution accuracy,
executability, prediction success, estimated cost, and the output path. It also
writes `result.json`, `result_summary.csv`, and readable per-task reports under
`runs/bird-schema-linking`. Exact predictions and scores can vary between model
calls.

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

## Explore the toolkit

- [Benchmarks](benchmarks.md) load questions, reference queries, and database
  connectors through one async interface.
- [Experiment runs](running-experiments.md) keep prediction, execution,
  evaluation, usage, and reports together.
- [Research agents](research-agents.md) cover direct prompting, schema-aware
  methods, ambiguity-aware SQL, and dbt transformations.
- [Evaluation](evaluation.md) combines task metrics with run-level aggregation.
