# Connecting data

Use `/connect` inside the Data Agent to add a file, database, graph, SPARQL
endpoint, or public dataset:

```text
/connect <source...> [--alias name]
```

Connections are available for the current session. TabulaFlow assigns an alias
automatically; use `--alias` when you want a short, predictable name to use in
prompts.

## Local files

Supported tabular formats are CSV, TSV, Excel (`.xlsx` and `.xls`), Parquet,
JSON, JSONL, and NDJSON.

```text
/connect ./data/orders.parquet
```

Relative paths resolve from the directory where you launched TabulaFlow. Each
file becomes a table named from its filename. Connect related files together to
load them as tables in one source:

```text
/connect ./data/customers.csv ./data/orders.csv --alias retail
```

## Local databases

SQLite (`.sqlite`, `.sqlite3`, and `.db`) and DuckDB (`.duckdb`) files can be
connected by path:

```text
/connect ./data/analytics.duckdb --alias analytics
```

## Database and graph servers

Packaged integrations include SQLite, DuckDB, PostgreSQL, MySQL, Snowflake,
BigQuery, Neo4j, and SPARQL endpoints.

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

TabulaFlow upgrades standard PostgreSQL, MySQL, and SQLite URLs to their async
drivers automatically. Preserve the exact `neo4j`, `neo4j+s`, `bolt`, or
`bolt+s` scheme supplied by your Neo4j deployment because it controls routing
and transport security.

## Public datasets

Connect Wikidata by its catalog name:

```text
/connect wikidata
```

Hugging Face dataset URLs are also supported:

```text
/connect https://huggingface.co/datasets/nyu-mll/glue/viewer/sst2/train
```

When a dataset has multiple configurations, TabulaFlow asks you to choose one.
Add `/viewer/<subset>/<split>` to the URL when you want to select both
explicitly.

## Source safety and the workspace

Every connected source is read-only. The agent can query it but cannot run
write statements against it. Derived tables, combined data, and extracted
records are written to the built-in local DuckDB workspace instead.

Sources connected under separate aliases cannot be joined directly. Ask the
agent to combine them; it will copy the relevant data into the workspace and
perform the join there.

## Credentials

Prefer environment variables, cloud-provider configuration, or your database
driver's credential mechanism. Avoid putting passwords in shell history,
committed files, prompts, or issue reports. If a URL must contain credentials,
percent-encode reserved characters and use a least-privilege read-only account.

Content needed to answer a prompt may be sent to the configured model provider.
See [Security and privacy](../reference/security-and-privacy.md) before
connecting sensitive data.

## Disconnect a source

```text
/disconnect warehouse
```

Run `/disconnect` without a name when exactly one user source is connected.
The built-in workspace cannot be disconnected.
