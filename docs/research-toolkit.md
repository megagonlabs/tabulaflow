# Research toolkit

TabulaFlow includes benchmark loaders, research agents, execution pipelines,
and evaluation metrics for text-to-query research.

## See available benchmarks

```bash
tabulaflow benchmark list
```

The registered benchmarks include BIRD-SQL, Spider 2.0, Beaver, ARCS,
AMBROSIA-S, and CypherBench.

## Download a managed benchmark

```bash
tabulaflow benchmark download cypherbench
```

Prerequisites differ by benchmark and may include local datasets, Docker,
manual setup, or cloud credentials. This page will document each supported
benchmark's exact setup before the beta release.
