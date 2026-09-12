# Research toolkit

Use TabulaFlow to load benchmarks, run text-to-query agents, execute their
predictions, and evaluate the results.

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

Setup differs by benchmark. You may need a local dataset, Docker, or cloud
credentials. Check [Benchmarks](benchmarks.md) before
you begin.
