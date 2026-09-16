# Quick start

TabulaFlow Research extends the main Python library for AI researchers working
on text-to-SQL and data agents. Its main building blocks include benchmark
loaders, agents, evaluation metrics, and experiment pipelines. It is
designed around principles that enable flexible, rapid, and transparent
experiments:

- **Benchmark-ready.** Run BIRD-SQL, Spider 2.0, Beaver, ARCS, AMBROSIA-S, and
  CypherBench with managed setup and official leaderboard metrics.
- **Reusable agent logic.** One agent implementation runs on all benchmarks.
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

## Example: Evaluate a full-schema agent

Run a full-schema agent on three BIRD-SQL tasks concurrently, execute its
queries, and measure execution accuracy:

```python title="research_quick_start.py"
--8<-- "examples/research_quick_start.py:example"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/research-quick-start.txt"
    ```

See [saving a run](running-experiments.md#save-and-restore-a-run) to export the result.

## Try it yourself

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) on macOS or
Linux. Download BIRD-SQL and set an OpenAI API key:

```bash
uvx --python 3.11 --from tabulaflow==0.1.0 tabulaflow benchmark download bird-sql
export OPENAI_API_KEY="your-api-key"
```

Run the example directly:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/research_quick_start.py
```

uv downloads the script and prepares Python and its dependencies. No project
setup or manual file creation is needed.
The example makes paid model calls; predictions and scores vary between runs.

??? info "Run from a source checkout"

    From the repository root:

    ```bash
    uv run tabulaflow benchmark download bird-sql
    uv run python docs/examples/research_quick_start.py
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

## Explore the toolkit

- [Benchmarks](benchmarks.md): choose, install, and load benchmark tasks.
- [Agents](agents.md): choose and configure a built-in method.
- [Running experiments](running-experiments.md): scale, save, and compare runs.
- [Evaluation and analysis](evaluation.md): choose metrics and inspect results.
- [Extend the toolkit](extending.md): use your own agents, datasets, and metrics.
- [API reference](api-reference.md): look up contracts, fields, and signatures.
