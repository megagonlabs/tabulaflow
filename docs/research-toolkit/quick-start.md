# Quick start

Run, compare, and develop text-to-query methods in Python with benchmark
loaders, agents, evaluation metrics, and typed results.

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

`simple` names the single-query contract, not task difficulty.

## Example: Evaluate a full-schema agent

Run a full-schema agent on three BIRD-SQL tasks concurrently, execute its
queries, and measure execution accuracy:

```python title="research_quick_start.py"
--8<-- "examples/research_quick_start.py"
```

The script prints a question, predicted SQL, its DataFrame result, and aggregate
accuracy. See [saving a run](running-experiments.md#save-a-run) to export the result.

## Try it yourself

Install TabulaFlow:

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

Save the example as `research_quick_start.py` and run:

```bash
uv run python research_quick_start.py
```

From a source checkout, run `uv run docs/examples/research_quick_start.py`.
The example makes paid model calls; predictions and scores vary between runs.

## Explore the toolkit

- [Benchmarks](benchmarks.md): choose, install, and load benchmark tasks.
- [Agents](agents.md): choose and configure a built-in method.
- [Running experiments](running-experiments.md): scale, save, and compare runs.
- [Evaluation and analysis](evaluation.md): choose metrics and inspect results.
- [Extending the toolkit](extending.md): implement and evaluate your own method.
- [API reference](api-reference.md): look up contracts, fields, and signatures.
