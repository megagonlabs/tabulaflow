# Benchmarks

| Benchmark | Task | Database | Splits |
| --- | --- | --- | --- |
| [BIRD-SQL](#bird-sql) | Text-to-SQL | SQLite | `dev`, `dev_20251106`, `train` |
| [Spider 2.0 Snow](#spider-20-snow) | Text-to-SQL | Snowflake | `test` |
| [Spider 2.0 Lite](#spider-20-lite) | Text-to-SQL | BigQuery, Snowflake, SQLite | `test` |
| [Spider 2.0 dbt](#spider-20-dbt) | Data transformation | DuckDB | `test` |
| [Beaver](#beaver) | Text-to-SQL | MySQL | `test` |
| [ARCS](#arcs) | Ambiguous text-to-SQL | SQLite | `test`, `test_unsampled` |
| [AMBROSIA](#ambrosia) | Ambiguous text-to-SQL | SQLite | `test`, `few_shot_examples` |
| [CypherBench](#cypherbench) | Text-to-Cypher | Neo4j | `test`, `train` |

Run the setup commands from a project with [TabulaFlow installed](quick-start.md#use-in-your-project).
Data is stored in `~/.tabulaflow/benchmarks/<name>/`. Check local installations
with `uv run tabulaflow benchmark list`.

## BIRD-SQL

Text-to-SQL questions with supporting evidence and column descriptions over
SQLite databases. The download includes tasks and databases for all splits;
`dev` uses the June 2024 release, while `dev_20251106` uses updated annotations.

```bash
uv run tabulaflow benchmark download bird-sql
```

## Spider 2.0 Snow

Text-to-SQL tasks over Snowflake databases. Download the tasks, schema metadata,
and reference results:

```bash
uv run tabulaflow benchmark download spider2-snow
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
uv run tabulaflow benchmark download spider2-lite
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
uv run tabulaflow benchmark download spider2-dbt
```

Use the [dbt agent](agents.md#dbt-transformations) to edit and run these projects.

## Beaver

[Beaver](https://github.com/beaverbench/beaver) contains enterprise text-to-SQL
tasks over MySQL databases. With Docker running, download the data and start
the databases:

```bash
uv run tabulaflow benchmark start beaver
```

The databases use local ports `3311` and `3312`. Stop them when finished:

```bash
uv run tabulaflow benchmark stop beaver
```

## ARCS

Ambiguous text-to-SQL tasks with annotated interpretations and intended
resolutions. ARCS requires manual setup. Place its task files and SQLite
databases in this layout:

```text
~/.tabulaflow/benchmarks/arcs/
├── tasks/
│   ├── tasks_unsampled.json
│   └── tasks_gold_intended_query_ids.json
└── databases/
    ├── column_meanings.json
    └── sqlite/
        ├── codebase_community.sqlite
        ├── financial.sqlite
        ├── github_repos.sqlite
        ├── professional_basketball.sqlite
        ├── retails.sqlite
        └── student_club.sqlite
```

For an existing data directory, pass its path as `directory` to the loader.

## AMBROSIA

Ambiguous text-to-SQL tasks covering scope, attachment, and vagueness.

```bash
uv run tabulaflow benchmark download ambrosia-s
```

## CypherBench

Text-to-Cypher tasks over Neo4j property graphs. With Docker running and
Docker Compose available, download the data and start the test databases:

```bash
uv run tabulaflow benchmark start cypherbench
```

Stop the databases when finished:

```bash
uv run tabulaflow benchmark stop cypherbench
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
database name to a live connector. See [resource cleanup](running-experiments.md#release-resources)
for closing them.
