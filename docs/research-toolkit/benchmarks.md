# Benchmarks

| Benchmark | Task | Database | Splits |
| --- | --- | --- | --- |
| [BIRD-SQL](#bird-sql) | Text-to-SQL | SQLite | `dev`, `dev_20251106`, `train` |
| [Spider 2.0 Snow](#spider-20-snow) | Text-to-SQL | Snowflake | `test` |
| [Spider 2.0 Lite](#spider-20-lite) | Text-to-SQL | SQLite, Snowflake, BigQuery | `test` |
| [Spider 2.0 dbt](#spider-20-dbt) | Data transformation | DuckDB | `test` |
| [Beaver](#beaver) | Text-to-SQL | MySQL | `test` |
| [AMBROSIA](#ambrosia) | Ambiguous text-to-SQL | SQLite | `test`, `few_shot_examples` |
| [CypherBench](#cypherbench) <span class="benchmark-tag benchmark-tag--official">official</span> | Text-to-Cypher | Neo4j | `test`, `train` |
| [ARCS](#arcs) <span class="benchmark-tag benchmark-tag--official">official</span> <span class="benchmark-tag benchmark-tag--new">new</span> | Ambiguous text-to-SQL | SQLite | `test`, `base` |

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
Download all splits (approximately 32 GB):

```bash
tabulaflow benchmark download bird-sql
```

Run five tasks with a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run bird-sql \
      --split dev \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run bird-sql \
      --split dev \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run bird-sql \
      --split dev \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run bird-sql \
      --split dev \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
      --sample-size 5
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
and reference results (approximately 0.8 GB):

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

Run five tasks with a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-snow \
      --split test \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-snow \
      --split test \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run spider2-snow \
      --split test \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-snow \
      --split test \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
      --sample-size 5
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
task assets and the local SQLite databases (approximately 2.7 GB):

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

Run five tasks against a local SQLite database with a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-lite \
      --split test \
      --database bank_sales_trading \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-lite \
      --split test \
      --database bank_sales_trading \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run spider2-lite \
      --split test \
      --database bank_sales_trading \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-lite \
      --split test \
      --database bank_sales_trading \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
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
the projects and their starting and reference databases (approximately 4 GB):

```bash
tabulaflow benchmark download spider2-dbt
```

Use the [dbt agent](api/agents.md#dbt-strategy) to edit and run these projects.

Run five tasks with a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-dbt \
      --split test \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-dbt \
      --split test \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run spider2-dbt \
      --split test \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run spider2-dbt \
      --split test \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
      --sample-size 5
    ```

<div class="benchmark-heading" markdown="1">

## Beaver

<div class="benchmark-resources" aria-label="Beaver resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2409.02038">Paper</a>
  <a class="benchmark-resource" href="https://beaverbench.github.io/">Website</a>
  <a class="benchmark-resource" href="https://huggingface.co/collections/beaverbench/beaver-dataset">Dataset</a>
</div>

</div>

Beaver contains enterprise text-to-SQL tasks over MySQL databases. Ensure that
[Docker is installed](https://docs.docker.com/get-started/get-docker/) and running,
then download the benchmark (approximately 4.2 GB) and start its databases:

```bash
tabulaflow benchmark download beaver
tabulaflow benchmark start beaver
```

The start command prints every database URL. Beaver uses these local endpoints:

| Database | URL |
| --- | --- |
| `dw` | `mysql://root:root@localhost:3311/dw` |
| `csail_stata_cinder`, `csail_stata_neutron`, `csail_stata_glance`, `csail_stata_nova`, `keystone` | `mysql://root:root@localhost:3312/<database>` |

Run five tasks with a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run beaver \
      --split test \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run beaver \
      --split test \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run beaver \
      --split test \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run beaver \
      --split test \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
      --sample-size 5
    ```

Stop the databases when finished:

```bash
tabulaflow benchmark stop beaver
```

<div class="benchmark-heading" markdown="1">

## AMBROSIA

<div class="benchmark-resources" aria-label="AMBROSIA resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2406.19073">Paper</a>
  <a class="benchmark-resource" href="https://ambrosia-benchmark.github.io/">Website</a>
</div>

</div>

Ambiguous text-to-SQL tasks covering scope, attachment, and vagueness.

Download the benchmark (approximately 0.1 GB):

```bash
tabulaflow benchmark download ambrosia-s
```

Run five tasks with a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run ambrosia-s \
      --split test \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run ambrosia-s \
      --split test \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run ambrosia-s \
      --split test \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run ambrosia-s \
      --split test \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
      --sample-size 5
    ```

<div class="benchmark-heading" markdown="1">

## CypherBench

<div class="benchmark-resources" aria-label="CypherBench resources">
  <a class="benchmark-resource" href="https://arxiv.org/pdf/2412.18702">Paper</a>
  <a class="benchmark-resource" href="https://github.com/megagonlabs/cypherbench">Website</a>
  <a class="benchmark-resource" href="https://huggingface.co/datasets/megagonlabs/cypherbench">Dataset</a>
</div>

</div>

CypherBench evaluates text-to-Cypher translation with more than 10,000
question–Cypher pairs across 11 large-scale Neo4j property graphs transformed
from Wikidata, totaling 7.8 million entities. Ensure that [Docker is
installed](https://docs.docker.com/get-started/get-docker/) and running, then
download the benchmark (approximately 5 GB):

```bash
tabulaflow benchmark download cypherbench
```

Start the database you plan to use:

```bash
tabulaflow benchmark start cypherbench \
  --split test \
  --database nba
```

To start all test databases at once, allow around 7 minutes for the first
import and use a machine with at least 48 GB of RAM. On machines with less
memory, start the databases individually with `--database` as shown above.

```bash
tabulaflow benchmark start cypherbench --split test
```

The start command prints the selected database URLs:

| Graph | Split | URL |
| --- | --- | --- |
| `art` | `train` | `bolt://localhost:15060` |
| `biology` | `train` | `bolt://localhost:15061` |
| `company` | `test` | `bolt://localhost:15062` |
| `fictional_character` | `test` | `bolt://localhost:15063` |
| `flight_accident` | `test` | `bolt://localhost:15064` |
| `geography` | `test` | `bolt://localhost:15065` |
| `movie` | `test` | `bolt://localhost:15066` |
| `nba` | `test` | `bolt://localhost:15067` |
| `politics` | `test` | `bolt://localhost:15068` |
| `soccer` | `train` | `bolt://localhost:15069` |
| `terrorist_attack` | `train` | `bolt://localhost:15070` |

The username is `neo4j` and the password is `cypherbench`.

!!! tip "Explore with the data agent"
    If you want to explore a running graph, [connect it directly in the TabulaFlow
    data agent](../data-agent/connecting-data.md#connect-directly):

    ```text
    /connect bolt://neo4j:cypherbench@localhost:15067 --alias nba
    ```

Run five tasks against the NBA database with a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run cypherbench \
      --split test \
      --database nba \
      --agent direct_prompting \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run cypherbench \
      --split test \
      --database nba \
      --agent direct_prompting \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run cypherbench \
      --split test \
      --database nba \
      --agent direct_prompting \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run cypherbench \
      --split test \
      --database nba \
      --agent direct_prompting \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
      --sample-size 5
    ```

When selecting tasks with `--qid` or `--sample-size`, only the databases used
by those tasks need to be running.

Stop a selected database when finished. Stopping removes its container, so the
next start imports it again:

```bash
tabulaflow benchmark stop cypherbench \
  --split test \
  --database nba
```

To stop all test databases instead:

```bash
tabulaflow benchmark stop cypherbench --split test
```

Use `--split train` with `start`, `run`, and `stop` when working with the
training split.

<div class="benchmark-heading" markdown="1">

## ARCS

<div class="benchmark-resources" aria-label="ARCS resources">
  <a class="benchmark-resource" href="https://huggingface.co/datasets/megagonlabs/arcs">Paper</a>
  <a class="benchmark-resource" href="../arcs/">Website</a>
  <a class="benchmark-resource" href="https://huggingface.co/datasets/megagonlabs/arcs">Dataset</a>
</div>

</div>

ARCS (**A**mbiguity **R**esolution **C**orpus for **S**QL) is a text-to-SQL
benchmark featuring naturally occurring, unconstrained ambiguities over
real-world databases, with complete annotations of valid ambiguity points,
interpretations, and SQL queries. The `test` split has 311 end-to-end
instances with intended resolution; `base` contains the 101 unique questions before sampling the resolution.

Download the tasks and six SQLite databases (approximately 9 GB):

```bash
tabulaflow benchmark download arcs
```

Run five tasks with the structured ambiguity agent and a
[configured model provider](../models.md#supported-providers):

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"

    tabulaflow benchmark run arcs \
      --split test \
      --llm openai:gpt-6-luna \
      --sample-size 5
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"

    tabulaflow benchmark run arcs \
      --split test \
      --llm anthropic:claude-sonnet-5 \
      --sample-size 5
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"

    tabulaflow benchmark run arcs \
      --split test \
      --llm vllm:Qwen/Qwen3-8B \
      --sample-size 5
    ```

=== "Fireworks AI"

    ```bash
    export FIREWORKS_API_KEY="your-api-key"

    tabulaflow benchmark run arcs \
      --split test \
      --llm fireworks:accounts/fireworks/models/kimi-k3 \
      --sample-size 5
    ```

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
