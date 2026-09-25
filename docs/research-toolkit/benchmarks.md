# Benchmarks

| Benchmark | Task | Database | Splits |
| --- | --- | --- | --- |
| [BIRD-SQL](#bird-sql) | Text-to-SQL | SQLite | `dev`, `dev_20251106`, `train` |
| [Spider 2.0 Snow](#spider-20-snow) | Text-to-SQL | Snowflake | `test` |
| [Spider 2.0 Lite](#spider-20-lite) | Text-to-SQL | BigQuery, Snowflake, SQLite | `test` |
| [Spider 2.0 dbt](#spider-20-dbt) | Data transformation | DuckDB | `test` |
| [Beaver](#beaver) | Text-to-SQL | MySQL | `test` |
| [ARCS](#arcs) (coming soon) | Ambiguous text-to-SQL | SQLite | `test`, `test_unsampled` |
| [AMBROSIA](#ambrosia) | Ambiguous text-to-SQL | SQLite | `test`, `few_shot_examples` |
| [CypherBench](#cypherbench) | Text-to-Cypher | Neo4j | `test`, `train` |

Run the setup commands after [installing the TabulaFlow tool](quick-start.md#try-it-yourself).
Data is stored in `~/.tabulaflow/benchmarks/<name>/`. Check local installations
with `tabulaflow benchmark list`.

## BIRD-SQL

Text-to-SQL questions with supporting evidence and column descriptions over
SQLite databases. The download includes tasks and databases for all splits;
`dev` uses the June 2024 release, while `dev_20251106` uses updated annotations.

```bash
tabulaflow benchmark download bird-sql
```

## Spider 2.0 Snow

Text-to-SQL tasks over Snowflake databases. Download the tasks, schema metadata,
and reference results:

```bash
tabulaflow benchmark download spider2-snow
```

Follow the [Spider 2.0 Snowflake access guide](https://github.com/xlang-ai/Spider2/blob/main/assets/Snowflake_Guideline.md)
to obtain database access and a programmatic access token, then set:

```bash
export SF_USER="your-username"
export SF_PASSWORD="your-programmatic-access-token"
export SF_ACCOUNT="your-account-identifier"
```

## Spider 2.0 Lite

Text-to-SQL tasks spanning BigQuery, Snowflake, and SQLite. The download includes
task assets and the local SQLite databases:

```bash
tabulaflow benchmark download spider2-lite
```

Configure credentials only for the databases you select. For setup, see the
[Snowflake access guide](https://github.com/xlang-ai/Spider2/blob/main/assets/Snowflake_Guideline.md)
or [Google Cloud authentication guide](https://docs.cloud.google.com/docs/authentication/provide-credentials-adc).

=== "SQLite"

    ```bash
    # No credentials or additional setup are needed.
    ```

=== "Snowflake"

    ```bash
    # Set your Spider 2.0 Snowflake credentials.
    export SF_USER="your-username"
    export SF_PASSWORD="your-programmatic-access-token"
    export SF_ACCOUNT="your-account-identifier"
    ```

=== "BigQuery"

    ```bash
    # Set your billing project.
    export GOOGLE_CLOUD_PROJECT="your-billing-project"

    # Sign in with the Google Cloud CLI.
    gcloud auth application-default login

    # Alternatively, use an existing service account:
    # export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
    ```

## Spider 2.0 dbt

Data transformation tasks in dbt projects backed by DuckDB. The download includes
the projects and their starting and reference databases:

```bash
tabulaflow benchmark download spider2-dbt
```

Use the [dbt agent](api/agents.md#dbt-strategy) to edit and run these projects.

## Beaver

[Beaver](https://github.com/beaverbench/beaver) contains enterprise text-to-SQL
tasks over MySQL databases. With Docker running, download the data and start
the databases:

```bash
tabulaflow benchmark start beaver
```

The databases use local ports `3311` and `3312`. Stop them when finished:

```bash
tabulaflow benchmark stop beaver
```

## ARCS

Coming soon.

## AMBROSIA

Ambiguous text-to-SQL tasks covering scope, attachment, and vagueness.

```bash
tabulaflow benchmark download ambrosia-s
```

## CypherBench

Text-to-Cypher tasks over Neo4j property graphs. With Docker running,
download the data and start the test databases:

```bash
tabulaflow benchmark start cypherbench
```

Stop the databases when finished:

```bash
tabulaflow benchmark stop cypherbench
```

For training databases, add `--split train` to both `start` and `stop`.

## Load in Python

After setup, choose a loader from the [loader reference](api/benchmarks.md#built-in-loaders).
All loaders share the same interface for loading tasks and database connectors.
For example, load three BIRD-SQL tasks:

```python
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader

loader = BirdSQLDatasetLoader()
dataset = await loader.get_split_async(
    "dev",
    qids=["3", "17", "42"],
)
```

Use `databases=["california_schools"]` to restrict databases or `subsample_size=10`
for a deterministic sample. Filtering precedes sampling.

`dataset.tasks` contains typed tasks. `dataset.db_connectors` maps each selected
database name to a live connector. Close them in a `finally` block, as shown in
the [quick start](quick-start.md#example-evaluate-a-full-schema-agent).
