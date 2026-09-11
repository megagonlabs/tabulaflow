# Connecting data

Run `/connect` in the Data Agent to add a file, database, graph, SPARQL
endpoint, or public dataset:

```text
/connect <source...> [--alias name]
```

Connections last for the current session. TabulaFlow creates an alias for each
source; use `--alias` to choose your own.

## Local files

You can connect CSV, TSV, Excel (`.xlsx` and `.xls`), Parquet, JSON, JSONL, and
NDJSON files.

```text
/connect ./data/orders.parquet
```

Relative paths start from the directory where you launched TabulaFlow. Each
file becomes a table named after the file. Connect related files together to
group them under one source:

```text
/connect ./data/customers.csv ./data/orders.csv --alias retail
```

## Local databases

Connect SQLite (`.sqlite`, `.sqlite3`, or `.db`) and DuckDB (`.duckdb`) files by
path:

```text
/connect ./data/analytics.duckdb --alias analytics
```

## Database and graph servers

TabulaFlow includes PostgreSQL, MySQL, Snowflake, BigQuery, Neo4j, and SPARQL
integrations.

| Source | Example |
| --- | --- |
| PostgreSQL | `postgresql://user@localhost/analytics` |
| MySQL | `mysql://user@localhost/analytics` |
| Snowflake | `snowflake://user@account/database` |
| BigQuery | `bigquery://project/dataset` |
| Neo4j | `neo4j+s://user@host?database=neo4j` |
| SPARQL | `sparql+https://example.org/sparql` |

```text
/connect postgresql://user@localhost/analytics --alias warehouse
```

TabulaFlow selects async drivers for PostgreSQL, MySQL, and SQLite. For Neo4j,
keep the exact `neo4j`, `neo4j+s`, `bolt`, or `bolt+s` scheme from your
deployment; it controls routing and transport security.

## Public datasets

Connect Wikidata by name:

```text
/connect wikidata
```

For a Hugging Face dataset, use its URL:

```text
/connect https://huggingface.co/datasets/nyu-mll/glue/viewer/sst2/train
```

If the dataset has multiple configurations, TabulaFlow asks you to choose one.
Add `/viewer/<subset>/<split>` to select both in the URL.

## Source safety and the workspace

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

## Credentials

Use environment variables, cloud-provider configuration, or your driver's
credential store. Keep passwords out of shell history, committed files,
prompts, and issue reports. If a URL must contain credentials, percent-encode
reserved characters and use a least-privilege read-only account.

TabulaFlow may send content needed for a prompt to your model provider. Review
[Security and privacy](../reference/security-and-privacy.md) before connecting
sensitive data.

## Disconnect a source

```text
/disconnect warehouse
```

If only one user source is connected, you can omit its name. You cannot
disconnect the built-in workspace.
