# Connecting data

You can ask the agent to connect a supported data source for you, or connect it
directly with `/connect`. Direct connections are useful when you want to choose
the alias yourself, start browsing immediately, or run TabulaFlow with the LLM
turned off. Once connected, you can browse the source directly with or without
an active LLM.

For example, ask the agent:

```text
Connect ./data/orders.parquet as orders.
```

## Connect directly

Run `/connect` in TabulaFlow:

```text
/connect <source...> [--alias name]
```

Connections last for the current session. TabulaFlow creates an alias for each
source; use `--alias` to choose your own.

## Choose your source

| You have | Connect with | Details |
| --- | --- | --- |
| CSV, Excel, Parquet, or JSON files | One or more file paths | [Local files](#local-files) |
| SQLite or DuckDB database | A database file path | [Local databases](#local-databases) |
| PostgreSQL, MySQL, Snowflake, or BigQuery | A connection URL | [SQL databases](#sql-databases) |
| Neo4j graph database | A `neo4j` or `bolt` URL | [Neo4j](#neo4j) |
| SPARQL endpoint | A `sparql+http` or `sparql+https` URL | [SPARQL](#sparql) |
| Hugging Face dataset | A dataset or viewer URL | [Hugging Face](#hugging-face) |
| Wikidata knowledge graph | The name `wikidata` | [Wikidata](#wikidata) |

## Local files

You can connect CSV, TSV, Excel (`.xlsx` and `.xls`), Parquet, JSON, JSONL, and
NDJSON files.

```text
/connect ./data/orders.parquet
```

Relative paths start from the directory where you launched TabulaFlow. Each
file is imported into a session-owned DuckDB table named after the file.
Connect related files together to group them under one source:

```text
/connect ./data/customers.csv ./data/orders.csv --alias retail
```

## Local databases

Connect SQLite (`.sqlite`, `.sqlite3`, or `.db`) and DuckDB (`.duckdb`) files by
path:

```text
/connect ./data/analytics.duckdb --alias analytics
```

## SQL databases

TabulaFlow includes PostgreSQL, MySQL, Snowflake, and BigQuery integrations.

| Source | Example |
| --- | --- |
| PostgreSQL | `postgresql://user@localhost/analytics` |
| MySQL | `mysql://user@localhost/analytics` |
| Snowflake | `snowflake://user@account/database` |
| BigQuery | `bigquery://project/dataset` |

```text
/connect postgresql://user@localhost/analytics --alias warehouse
```

TabulaFlow automatically selects async drivers for PostgreSQL and MySQL.

## Neo4j

Connect a Neo4j database with the URL provided by your deployment:

```text
/connect neo4j+s://user@host?database=neo4j --alias graph
```

Keep the exact `neo4j`, `neo4j+s`, `bolt`, or `bolt+s` scheme. It controls
routing, transport security, and certificate verification.

## SPARQL

Prefix the endpoint URL with `sparql+`:

```text
/connect sparql+https://example.org/sparql --alias knowledge_graph
```

TabulaFlow does not infer that a plain HTTP URL is a SPARQL endpoint.

## Hugging Face

Connect a dataset with its Hugging Face URL:

```text
/connect https://huggingface.co/datasets/nyu-mll/glue/viewer/sst2/train
```

If a dataset has multiple configurations, TabulaFlow asks you to choose one.
Add `/viewer/<subset>/<split>` to the URL to select both directly.

## Wikidata

Connect the Wikidata knowledge graph by name:

```text
/connect wikidata
```

TabulaFlow connects to the Wikidata Query Service as a SPARQL source and
provides source-specific query guidance to the agent.

## How connections work

### Source safety and the workspace

Connected sources are read-only. TabulaFlow writes derived tables, combined
data, and extracted records to its local DuckDB workspace.

<figure class="media-placeholder media-placeholder--diagram" aria-label="Placeholder for a diagram explaining a cross-source join in the local workspace">
  <div class="media-placeholder__content">
    <span class="media-placeholder__type">Diagram · wide</span>
    <strong>Combine read-only sources in the workspace</strong>
    <span>Show selected data flowing from customers.csv and a warehouse database into the local workspace, where the agent joins them and creates the result.</span>
  </div>
  <figcaption>Production placeholder · Mark both external sources as read-only and the workspace as writable.</figcaption>
</figure>

To join sources with different aliases, ask the agent to combine them in the
workspace.

### Credentials

Use environment variables, cloud-provider configuration, or your driver's
credential store. Keep passwords out of shell history, committed files,
prompts, and issue reports. If a URL must contain credentials, percent-encode
reserved characters and use a least-privilege read-only account.

TabulaFlow may send content needed for a prompt to your model provider. Review
your provider's data-handling and retention policies before connecting
sensitive data.

### Disconnect a source

```text
/disconnect warehouse
```

If only one user source is connected, you can omit its name. You cannot
disconnect the built-in workspace.
