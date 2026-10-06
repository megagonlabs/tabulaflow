# ARCS: Towards Precise Text-to-SQL via Structured Disambiguation

This TabulaFlow repository is the official code repository for
[ARCS](https://megagonlabs.github.io/tabulaflow/research/arcs/). It
provides the reference implementation for downloading, running, and evaluating
the benchmark.

## Get started

Install the TabulaFlow command-line tool, download ARCS, and run a small
experiment:

```bash
uv tool install tabulaflow
tabulaflow benchmark download arcs
tabulaflow benchmark run arcs --split test --sample-size 5
```

See the [ARCS setup guide](https://megagonlabs.github.io/tabulaflow/research/benchmarks/#arcs)
for model-provider configuration and other details.

## Code

- [`benchmarks/arcs.py`](benchmarks/arcs.py): dataset installation, task loading,
  and SQLite connectors
- [`agents/ambig_structured.py`](agents/ambig_structured.py): default structured
  ambiguity detection, resolution, and SQL generation agent
- [`agents/ambig_simple.py`](agents/ambig_simple.py): conversational ambiguity
  resolution agent
- [`agents/ambig_flat.py`](agents/ambig_flat.py): flat interpretation-generation
  agent
- [`metrics/ambig_point_stats.py`](metrics/ambig_point_stats.py): ambiguity-point
  and interpretation evaluation
- [`metrics/gold_ambig_point_stats.py`](metrics/gold_ambig_point_stats.py): gold
  ambiguity statistics
- [`../examples/ambiguity_aware_queries.py`](../examples/ambiguity_aware_queries.py):
  end-to-end Python example

The full dataset, annotations, and SQLite databases are available from the
[ARCS dataset repository](https://huggingface.co/datasets/megagonlabs/arcs).
