# Connect data

You can ask the agent to connect a supported data source for you, or connect it
directly with `/connect`. Direct connections are useful when you want to choose
the alias yourself, start browsing immediately, or run TabulaFlow with the LLM
turned off. Once connected, the source appears in the Data Explorer, where you
can browse its schemas, tables, and data without an active LLM.

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
| SQL database supported by SQLAlchemy | A connection URL | [SQL databases](#sql-databases) |
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

TabulaFlow accepts SQLAlchemy-compatible database URLs. Drivers for PostgreSQL,
MySQL, Snowflake, and BigQuery are included; other SQLAlchemy dialects can be
used when their required driver packages are installed.

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

Use the connection URI supplied by your Neo4j deployment unchanged, including
its scheme (`neo4j`, `neo4j+s`, `bolt`, or `bolt+s`). Do not replace it with the
scheme shown in this example: the scheme determines routing, TLS, and
certificate verification.

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

## Source safety and the workspace

Connected sources are read-only, so browsing and analysis do not change the
original data. The agent uses a local DuckDB workspace as its writable area,
storing anything it needs to create or retain for the session, including
intermediate results, transformed or combined data, and extracted records.
You can ask the agent at any time to export results to local files in any
format you need for saving, sharing, or further use.

## Credentials

Use environment variables, cloud-provider configuration, or your driver's
credential store. Keep passwords out of shell history, committed files,
prompts, and issue reports. If a URL must contain credentials, percent-encode
reserved characters and use a least-privilege read-only account.

TabulaFlow may send content needed for a prompt to your model provider. Review
your provider's data-handling and retention policies before connecting
sensitive data.

## Disconnect a source

```text
/disconnect warehouse
```
