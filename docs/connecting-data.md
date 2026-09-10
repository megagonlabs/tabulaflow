# Connecting data

Use `/connect` in the Data Agent to connect a source. TabulaFlow can query
connected sources directly and stores derived data in a local DuckDB workspace.

## Local files

Supported formats include CSV, TSV, Excel, Parquet, JSON, JSONL, and NDJSON.

```text
/connect ./data/orders.parquet
```

## Databases

Packaged integrations include SQLite, DuckDB, PostgreSQL, MySQL, Snowflake,
BigQuery, Neo4j, and SPARQL endpoints.

```text
/connect postgresql://user@localhost/analytics
```

Avoid placing passwords directly in commands or committed files. Prefer your
database driver's supported credential and environment configuration.

## Public datasets

Hugging Face dataset URLs and Wikidata are supported as queryable sources.

```text
/connect https://huggingface.co/datasets/nyu-mll/glue/viewer/sst2/train
```

Some datasets require a subset or split. TabulaFlow reports the available
choices when the URL is ambiguous.
