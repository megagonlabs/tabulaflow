# TabulaFlow

TabulaFlow is an open-source data agent and text-to-query toolkit for working
with databases, local files, documents, and the web. It combines an interactive
terminal application for data work with reusable components for NL2SQL and
text-to-query research.

> [!NOTE]
> TabulaFlow is currently alpha software. Interfaces and behavior may change
> before the first stable release.

## Features

- Query SQL databases, graph databases, SPARQL endpoints, and local data files
  using natural language.
- Explore schemas and combine data from multiple sources in a writable local
  workspace.
- Build structured datasets from web pages, documents, and collections of
  independent tasks.
- Present results as tables, charts, maps, and graphs in a browser output pane.
- Use reusable async data, output, and agent layers in Python applications.
- Run and evaluate text-to-query research on BIRD-SQL, Spider 2.0, Beaver,
  ARCS, AMBROSIA-S, and CypherBench.

## Requirements

- Python 3.11, 3.12, or 3.13
- macOS or Linux
- An API key for a supported model provider to use the agent
- [`uv`](https://docs.astral.sh/uv/) for the recommended installation

Some connectors and research benchmarks require their own database credentials
or services.

## Installation

Install the command-line application with `uv`:

```bash
uv tool install tabulaflow
uv tool run --from playwright playwright install chromium
```

The second command installs the browser used by TabulaFlow's web tools. To
install the latest source checkout instead of the published package:

```bash
git clone https://github.com/megagonlabs/tabulaflow.git
cd tabulaflow
uv tool install --editable .
uv tool run --from playwright playwright install chromium
```

## Quick start

Set a provider API key, move to the project whose files TabulaFlow should be
able to access, and launch the application:

```bash
export OPENAI_API_KEY="your-api-key"
cd /path/to/your/project
tabulaflow
```

TabulaFlow treats the launch directory as the project directory. Relative file
paths and shell commands resolve from that directory.

The application includes a small sample dataset. Try asking:

```text
Using the sample data, show the five merchants with the highest total spend as
a bar chart.
```

Use `/connect` in the application to connect a CSV, Excel workbook, JSON or
Parquet file, a Hugging Face dataset, or a supported database. Without a
configured provider key, TabulaFlow can start with the LLM disabled.

Run `tabulaflow --help` to see launch configuration, including model presets,
schema caching, service tier, logging, and output-pane settings.

## What you can do

Examples of tasks TabulaFlow is designed to handle include:

- "Analyze monthly revenue in `sales.csv` and chart the trend."
- "Which tables in this PostgreSQL database contain customer information?"
- "Compare these two datasets and explain where their coverage differs."
- "Extract every product and price from these documents into a clean table."
- "Map the locations in this query result."
- "Classify each support ticket by topic using parallel subagents."

TabulaFlow can inspect and transform data, browse the web, edit files, and run
shell commands. Review proposed tasks and outputs carefully when working with
sensitive data or repositories.

## Research toolkit

TabulaFlow also contains benchmark loaders, research agents, execution tools,
and evaluation metrics for text-to-query research. Benchmark data is installed
under `~/.tabulaflow/benchmarks` rather than downloaded during experiments.

```bash
tabulaflow benchmark list
tabulaflow benchmark download cypherbench
tabulaflow benchmark start cypherbench
```

The core experiment pipeline consists of prediction, query execution, and
evaluation:

```bash
uv run tabulaflow/research/pipelines/predict.py \
  --agent schema_linking \
  --dataset bird-sql \
  --output-dir output/test
uv run tabulaflow/research/pipelines/execute.py output/test
uv run tabulaflow/research/pipelines/evaluate.py output/test
```

Available benchmark keys include `bird-sql`, `spider2-snow`, `spider2-lite`,
`spider2-dbt`, `beaver`, `arcs`, `ambrosia-s`, and `cypherbench`. External
services and credentials are required for some datasets.

## Python package structure

The package follows an enforced layered architecture:

```text
tabulaflow/
├── core/       Stable result, schema, media, and serialization primitives
├── data/       Connectors, registries, schema services, and data loaders
├── output/     Result storage, formatting, and visualization specifications
├── agents/     Agent runtime, chat sessions, extraction, and tools
├── app/        Terminal application and browser output pane
└── research/   Benchmarks, research agents, pipelines, and metrics
```

The product layers are ordered `core < data < output < agents < app`.
`research` is a separate consumer of the reusable platform layers.

## Development

Clone the repository and install all development dependencies:

```bash
git clone https://github.com/megagonlabs/tabulaflow.git
cd tabulaflow
make sync
```

Common checks are:

```bash
make format       # format and apply safe lint fixes
make lint         # run Ruff
make mypy         # run strict type checking
make lint-arch    # verify package dependency boundaries
make test         # run the test suite
```

Use `uv` for Python commands and dependency management. Do not commit API keys,
database credentials, local benchmark data, caches, or experiment outputs.

## Project status

TabulaFlow is under active development. The `0.x` releases should be treated as
experimental: configuration, Python APIs, and command behavior may change as
the project approaches a stable release.

Please use [GitHub Issues](https://github.com/megagonlabs/tabulaflow/issues) to
report reproducible bugs or request features.

## License

TabulaFlow is distributed under the [BSD 3-Clause License](LICENSE).
