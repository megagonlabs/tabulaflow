# TabulaFlow

TabulaFlow is an open-source project with three components:

1. **Data Agent** — An interactive app for analyzing, transforming, and
   visualizing data from databases, files, public datasets, and the web.
2. **Python Library** — Reusable components for building custom data agents and
   other data applications.
3. **Research Toolkit** — Tools for building and evaluating text-to-query agents
   on established benchmarks.

> [!NOTE]
> TabulaFlow 0.1.0 is a public beta. Minor `0.x` releases may contain documented
> breaking changes.

## Install

TabulaFlow requires Python 3.11 or later and supports macOS and Linux. Install
the Data Agent with [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install tabulaflow
uv tool run --from playwright playwright install chromium
```

For use as a Python library:

```bash
pip install tabulaflow
```

## Quick start

Set an OpenAI or Anthropic API key, then launch TabulaFlow from the directory it
should work in:

```bash
export OPENAI_API_KEY="your-api-key"
cd /path/to/your/project
tabulaflow
```

TabulaFlow automatically selects a model preset from the available credentials.
Use `/config` to change it. Without a supported key, the app starts with the LLM
disabled while data connection and browsing remain available.

The app includes sample data, so you can start with:

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

Use `/connect` to add local files, Hugging Face datasets, Wikidata, or supported
databases.

## Capabilities

- Query SQL databases, Neo4j graphs, SPARQL endpoints, and local data files.
- Explore schemas and combine sources in a writable local workspace.
- Gather and structure data from web pages and documents.
- Transform and enrich datasets with parallel semantic operations.
- Present results as tables, charts, maps, and graphs.
- Build on reusable async connectors, agents, tools, and output APIs.

Supported local formats include CSV, TSV, Excel, Parquet, JSON, JSONL, and
NDJSON. Packaged database integrations include SQLite, DuckDB, PostgreSQL,
MySQL, Snowflake, BigQuery, Neo4j, and SPARQL.

## Research toolkit

TabulaFlow provides benchmark loaders, research agents, execution pipelines,
and evaluation metrics for BIRD-SQL, Spider 2.0, Beaver, ARCS, AMBROSIA-S, and
CypherBench.

```bash
tabulaflow benchmark list
tabulaflow benchmark download cypherbench
```

Benchmarks have different prerequisites, including local data, Docker, manual
dataset setup, or cloud credentials.

## Privacy and security

TabulaFlow stores session data locally. Prompts and relevant tool results may be
sent to the configured model provider. TabulaFlow sends no telemetry to Megagon
Labs.

TabulaFlow is not a sandbox. Its file, shell, and browser tools operate with the
current user's permissions. Run it in trusted environments and use
least-privilege credentials. See [SECURITY.md](SECURITY.md) for reporting and
security guidance.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution
guidelines. Release notes are published with
[GitHub Releases](https://github.com/megagonlabs/tabulaflow/releases).

## License

TabulaFlow is distributed under the [BSD 3-Clause License](LICENSE).
