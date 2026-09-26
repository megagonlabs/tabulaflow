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

<div class="benchmark-heading" markdown="1">

## BIRD-SQL

<div class="benchmark-resources" aria-label="BIRD-SQL resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2305.03111">Paper</a>
  <a class="benchmark-resource" href="https://bird-bench.github.io/">Website</a>
</div>

</div>

Text-to-SQL questions with supporting evidence and column descriptions over
SQLite databases. The download includes tasks and databases for all splits;
`dev` uses the June 2024 release, while `dev_20251106` uses updated annotations.

```bash
tabulaflow benchmark download bird-sql
```

```bash
tabulaflow benchmark run bird-sql --split dev --sample-size 5
```

<div class="benchmark-heading" markdown="1">

## Spider 2.0 Snow

<div class="benchmark-resources" aria-label="Spider 2.0 Snow resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2411.07763">Paper</a>
  <a class="benchmark-resource" href="https://spider2-sql.github.io/">Website</a>
  <a class="benchmark-resource" href="https://github.com/xlang-ai/Spider2/tree/main/spider2-snow">Dataset</a>
</div>

</div>

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

```bash
tabulaflow benchmark run spider2-snow --split test --sample-size 5
```

<div class="benchmark-heading" markdown="1">

## Spider 2.0 Lite

<div class="benchmark-resources" aria-label="Spider 2.0 Lite resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2411.07763">Paper</a>
  <a class="benchmark-resource" href="https://spider2-sql.github.io/">Website</a>
  <a class="benchmark-resource" href="https://github.com/xlang-ai/Spider2/tree/main/spider2-lite">Dataset</a>
</div>

</div>

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

Run five tasks against a local SQLite database:

```bash
tabulaflow benchmark run spider2-lite \
  --split test \
  --database bank_sales_trading \
  --sample-size 5
```

<div class="benchmark-heading" markdown="1">

## Spider 2.0 dbt

<div class="benchmark-resources" aria-label="Spider 2.0 dbt resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2411.07763">Paper</a>
  <a class="benchmark-resource" href="https://spider2-sql.github.io/">Website</a>
  <a class="benchmark-resource" href="https://github.com/xlang-ai/Spider2/tree/main/spider2-dbt">Dataset</a>
</div>

</div>

Data transformation tasks in dbt projects backed by DuckDB. The download includes
the projects and their starting and reference databases:

```bash
tabulaflow benchmark download spider2-dbt
```

Use the [dbt agent](api/agents.md#dbt-strategy) to edit and run these projects.

```bash
tabulaflow benchmark run spider2-dbt --split test --sample-size 5
```

<div class="benchmark-heading" markdown="1">

## Beaver

<div class="benchmark-resources" aria-label="Beaver resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2409.02038">Paper</a>
  <a class="benchmark-resource" href="https://beaverbench.github.io/">Website</a>
  <a class="benchmark-resource" href="https://huggingface.co/collections/beaverbench/beaver-dataset">Dataset</a>
</div>

</div>

Beaver contains enterprise text-to-SQL tasks over MySQL databases. Download the
benchmark, then start its databases with Docker running:

```bash
tabulaflow benchmark download beaver
tabulaflow benchmark start beaver
```

```bash
tabulaflow benchmark run beaver --split test --sample-size 5
```

The databases use local ports `3311` and `3312`. Stop them when finished:

```bash
tabulaflow benchmark stop beaver
```

<div class="benchmark-heading" markdown="1">

## ARCS

<div class="benchmark-resources" aria-label="ARCS resources">
  <span class="benchmark-resource benchmark-resource--unavailable">Paper forthcoming</span>
  <span class="benchmark-resource benchmark-resource--unavailable">Website forthcoming</span>
  <span class="benchmark-resource benchmark-resource--unavailable">Dataset forthcoming</span>
</div>

</div>

Coming soon.

<div class="benchmark-heading" markdown="1">

## AMBROSIA

<div class="benchmark-resources" aria-label="AMBROSIA resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2406.19073">Paper</a>
  <a class="benchmark-resource" href="https://ambrosia-benchmark.github.io/">Website</a>
</div>

</div>

Ambiguous text-to-SQL tasks covering scope, attachment, and vagueness.

```bash
tabulaflow benchmark download ambrosia-s
```

```bash
tabulaflow benchmark run ambrosia-s --split test --sample-size 5
```

<div class="benchmark-heading" markdown="1">

## CypherBench

<div class="benchmark-resources" aria-label="CypherBench resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2412.18702">Paper</a>
  <a class="benchmark-resource" href="https://github.com/megagonlabs/cypherbench">Website</a>
  <a class="benchmark-resource" href="https://huggingface.co/datasets/megagonlabs/cypherbench">Dataset</a>
</div>

</div>

Text-to-Cypher tasks over Neo4j property graphs. Download the benchmark, then
start the test databases with Docker running. Starting imports each graph into
Neo4j, which can take a while:

```bash
tabulaflow benchmark download cypherbench
tabulaflow benchmark start cypherbench
```

```bash
tabulaflow benchmark run cypherbench --split test --sample-size 5
```

Stop the databases when finished (this removes the containers, so the
next start imports again):

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
