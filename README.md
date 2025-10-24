# mintq

A **Min**imalist **T**ext-to-**Q**uery Library that offers:

📐 **Everything Structured**: All data—including database schemas—is structured and explicitly [defined](mintq/schema.py). No more dealing with complex black-box dictionaries or parsing massive schema strings.

🔍 **Type-safe**: Every method is type-hinted and checked with static type checker mypy.

🧩 **Modular**: Core components like [database connectors](mintq/db_connector/base.py), [dataloaders](mintq/datahub/base.py), [agents](mintq/agenthub/base.py), [tools](mintq/toolhub/base.py), [metrics](mintq/metrics/base.py) follow the interfaces defined in the base.py files.

🔌 **Extensible**: Intefaces are designed to be minimal and flexible, without heavy abstractions. You are free to use any agent library to build your own text-to-query agent.

🌐 **Multi-DBMS**: Works with a wide variety of databases including all SQL databases (e.g. PostgreSQL, MySQL, SQLite) supported by sqlalchemy as well as graph databases like Neo4j.

⚡ **First-class Asyncio Support**: The library is built with asyncio with built-in rate limiting and maximum concurrency control.

🧠 **Built for Researchers**: Key features:
- Out-of-the-box support for BIRD-SQL, Beaver, Spider 2.0 and ARCS
- Equivalent re-implementation of official leaderboard metrics
- Re-implementation of state-of-the-art agents on leaderboards
- Lightning-fast inference and evaluation using asyncio
- Tracing with langfuse and other LLM observability platforms
- Local trajectory tracing
- Agent tool call and token usage tracking
- Support for interactive task with user simulator
- Schema compression for database with thousands of tables

## 🚀 Quick Start

### Installation

First, follow the [Development](#-development) section to install the library. Next, follow the [Dataset Setup](#-dataset-setup) section to download the datasets you want to use.

### Using `mintq` as a library

```python
import asyncio
from mintq.agenthub import SQLAgent, BasicAgentConfig
from mintq.datahub import BirdSQLDatasetLoader
from mintq.metrics import BirdSQLEx
from mintq.pipelines import run_agent_async, populate_exec_results_async, evaluate_async


async def main() -> None:
    dataloader = BirdSQLDatasetLoader()
    # dataset includes the text-to-query tasks and the database connectors
    dataset = await dataloader.get_split_async("dev")
    dataset.tasks = dataset.tasks[:3]

    # define the model arguments
    # the `run_model` function below uses this to construct a separate model instance for each sample to avoid race condition
    config = BasicAgentConfig(llm="openai:gpt-4.1-mini", schema_formatter="sql_default")
    # run the model on the dataset using async coroutines
    result = await run_agent_async(SQLAgent, config, dataset, batch_size=2)
    print(result.tasks[0].pred_query.query)
    # SELECT MAX(CASE WHEN "Enrollment (K-12)" > 0 THEN "Free Meal Count (K-12)" / "Enrollment (K-12)" ELSE NULL END) AS Highest_Eligible_Free_Rate
    # FROM frpm
    # WHERE "County Name" = 'Alameda' AND "Enrollment (K-12)" > 0;
    print()
    print(result.aggregated_inference_metrics)
    # {'latency_seconds': {'avg': 7.4654, ...

    # populate exec results
    result = await populate_exec_results_async(result, dataset, batch_size=2, timeout=30)

    # evaluate execution accuracy
    metrics = [BirdSQLEx()]
    result_with_metrics = await evaluate_async(result, metrics, batch_size=2)
    print(result_with_metrics.aggregated_eval_metrics)
    # {'bird_sql_ex': {'avg': 0.3333}}


if __name__ == "__main__":
    asyncio.run(main())

```

### Running experiments with provided scripts

We also provide the [run_model.py](mintq/run_model.py) and [evaluate.py](mintq/evaluate.py) scripts for convenience:

```bash
uv run mintq/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --llm "openai:gpt-4o-mini" --result_dir output/test/ --debug
uv run mintq/pipelines/populate_exec_results.py --result_dir output/test/
uv run mintq/pipelines/evaluate.py --result_dir output/test/
```

## Project Structure

```
mintq
├── agenthub/               # text-to-query methods
│   ├── simple_zero_shot.py
│   ├── sql_agent.py
│   └── ...
├── toolhub/                # tools used by agents
│   ├── search_keywords.py
│   ├── run_query.py
│   ├── finish.py
│   ├── ask_user.py
│   ├── get_schema.py
│   └── ...
├── datahub/                # text-to-query datasets
│   ├── bird_sql.py
│   ├── spider2.py
│   ├── beaver.py
│   ├── arcs.py
│   └── ...
├── db_connector/           # database connectors
│   ├── sql_conn.py
│   └── ...
├── metrics/                 # evaluation metrics
│   ├── bird_sql_ex.py
│   ├── executable.py
│   └── ...
├── metadata_synthesizer/   # metadata generation methods
│   ├── er_diagram.py       # ER diagram inference
│   └── ...
├── formatters/       # database schema formatters
│   ├── sql.py
│   └── ...
├── pipelines/              # pipelines
│   ├── run_agent.py
│   ├── populate_exec_results.py
│   ├── evaluate.py
│   └── ...
├── schema.py               # data structures used in the project
├── config.py
├── registry.py
└── utils.py                # utility functions
```

## 📚 Dataset Setup

Currently, the following datasets are supported:

| Dataset | Key | Splits |
|---------|-----|------------------|
| BIRD-SQL | `bird-sql` | `train`, `dev` |
| Spider 2.0-snow | `spider2-snow` | `dev`|
| Spider 2.0-simple (from Aaron) | `spider2-simple` | `dev` |
| Beaver | `beaver` | `dev` |

### BIRD-SQL

Download the BIRD-SQL dataset from [here](https://bird-bench.github.io/).

The dataset should be stored in the `data/bird-sql` directory and organized as follows:

```
data/
├── BIRD-SQL/
│   ├── train/
│   |   └── ...
│   └── dev_20240627/
│       ├── dev_databases/
│       ├── dev.json
│       └── ...
└── ...
```

### Spider 2.0

First, follow the guidelines [here](https://github.com/xlang-ai/Spider2/blob/main/assets/Snowflake_Guideline.md) to request a Snowflake account.

Configure the credentials using environment variables:

```bash
export SF_USER="your_username"
export SF_PASSWORD="your_password"
export SF_ACCOUNT="RSRSBDK-YDB67606"
```

Next, clone the Spider2 repository and save it as `data/Spider2`:

```bash
git clone https://github.com/xlang-ai/Spider2.git data/Spider2
```

To run the simplied Spider 2.0 snow dataset, export the Google spreadsheet as a CSV file and save it as `data/spider2-simple/spider2-simple-v1.csv`. Then, run the run_model.py and evaluate.py scripts as shown in the Quick Start section. The results will be available in the `result_with_metrics.csv` file which you can then import into Google spreadsheet.

### Beaver

Download the Beaver dataset from [here](https://github.com/peterbaile/beaver).

The dataset should be stored in the `data/beaver` directory and organized as follows:

```
data/
├── beaver/
│   ├── dw/
│   │   └── new_dw_indexed.sql
│   ├── nw/
│   │   ├── keystone.sql
│   │   ├── csail_stata_neutron.sql
│   │   └── ...
│   ├── dev_dw.json
│   ├── dev_nw.json
│   ├── test_dw.json
│   └── test_nw.json
└── ...
```

Run the following command to start the MySQL databases:

```bash
docker run -d --name beaver-dw -p 3311:3306 -e MYSQL_ROOT_PASSWORD=root -v $(pwd)/data/beaver/dw:/docker-entrypoint-initdb.d mysql:8.0 --lower-case-table-names=1
```

```bash
docker run -d --name beaver-nw -p 3312:3306 -e MYSQL_ROOT_PASSWORD=root -v $(pwd)/data/beaver/nw:/docker-entrypoint-initdb.d mysql:8.0 --lower-case-table-names=1
```

## AMBROSIA-S (Structured)

**Original Data**

Download the AMBROSIA dataset (`data.zip`) from [here](https://ambrosia-benchmark.github.io/).

Unzip the archive and move its contents into `data/ambrosia_s/`:

```bash
unzip data.zip && mv data data/ambrosia_s/ambrosia
```

Next, download the structured disambiguation annotations from Google Drive:

```bash
uvx gdown "https://drive.google.com/uc?id=1Zqx4sVuQGWZuyuT91OY3tnARC6Tz6EQp" -O data/ambrosia_s/ambrosia_few_shot_examples.json
uvx gdown "https://drive.google.com/uc?id=1cYftWIdRQfOVaHSVuSjOA4XjfcOvodk2" -O data/ambrosia_s/ambrosia_test.json
```

Finally, run the following scripts to add question texts and gold queries to the annotations:

```bash
uv run python scripts/ambrosia_s/add_values_to_annotations.py --csv data/ambrosia_s/ambrosia/ambrosia.csv --input data/ambrosia_s/ambrosia_few_shot_examples.json --output data/ambrosia_s/ambrosia_few_shot_examples_processed.json
uv run python scripts/ambrosia_s/add_values_to_annotations.py --csv data/ambrosia_s/ambrosia/ambrosia.csv --input data/ambrosia_s/ambrosia_test.json --output data/ambrosia_s/ambrosia_test_processed.json
```

```
data/ambrosia_s
├── ambrosia_few_shot_examples_processed.json  # processed annotations from the "few_shot_examples" split
├── ambrosia_few_shot_examples.json  # structured disambiguation annotations from the "few_shot_examples" split
├── ambrosia_test_processed.json  # processed annotations from the "test" split
├── ambrosia_test.json  # structured disambiguation annotations from the "test" split
├── ambrosia
│   ├── ambrosia.csv  # main csv file
│   ├── attachment    # DB files for "attachment" ambiguity type
│   ├── scope  # DB files for "scope" ambiguity type
│   └── vague  # DB Files for "vague" ambiguity type
├── ...
```


## 💻 Development

### Dependencies

We use `uv` to manage dependencies (the modern replacement of pip/conda/poetry).

First, run `uv --version` to ensure that [uv](https://docs.astral.sh/uv/getting-started/installation/) is installed.

After cloning the repository, run `uv venv` to create a local venv at `.venv/`. Then run `make sync` (which runs [`uv sync`](Makefile#L3) behind the scenes) to install the dependencies into the venv.

To add a new dependency, run `uv add <dependency>`. The `pyproject.toml` file and `uv.lock` should be committed to the repository.

To run a python script, run `uv run <script.py>` (this is the preferred way but you can also either activate the venv using `source .venv/bin/activate` first or directly run the python binary `.venv/bin/python <script.py>`).

### Environment variables

We use `direnv` to manage environment variables.

First, run `direnv --version` to ensure that [direnv](https://direnv.net/) is installed.

Next, create a `.envrc` file in the root directory and add the environment variables to it. This file should NOT be committed to the repository.

```bash
export OPENAI_API_KEY="your_openai_api_key"

# for Spider 2.0 (optional)
export SF_USER="your_snowflake_username"
export SF_PASSWORD="your_snowflake_password"
export SF_ACCOUNT="RSRSBDK-YDB67606"

# for tracing (optional)
export OTEL_EXPORTER_OTLP_ENDPOINT="your_opentelemetry_endpoint"
export LOGFIRE_TOKEN="your_logfire_token"
```

Then, run `direnv allow` to load the environment variables. In the future, the env vars will be loaded automatically when you enter the directory.

### Utility commands

We use `make` to manage a few common commands we frequently use (see [`Makefile`](Makefile) for their definitions):

```bash
make format      # format and lint
make mypy        # type check with mypy
make test-simple # test simple_zero_shot
make test-agent  # test sql_agent_table_names_only
make sync        # sync the dependencies in pyproject.toml into the venv (e.g. when others have updated the dependencies)
```


---

Contact: yanlin@megagon.ai

## Roadmap

### Agent

- [x] Agent V2 starting with table names and foreign keys, with tools `list_columns`, `search_keywords`, `run_query`
- [x] Reproduce performance of Agent V1
- [ ] Hierarchical schemas
  - [x] HSchema generation v1
  - [x] HSchema generation v2
  - [x] HSchema formatting
  - [x] Design tools
  - [x] Benchmark performance: `bird-sql.dev_199: 64.32 / 68.34 (soft)` `spider2-snow.dev_63: 25.40`
  - [ ] Support grouping tables with date suffixes (e.g. `order_20240627`)
- [x] Add table and column descriptions
- [ ] Foreign key inference
- [ ] Orchestrator + Schema linking agent + SQL writing agent + Final refinement agent
- [ ] JOIN discovery agent
- [ ] Code diff tool
- [ ] Tools for control columns like `is_deleted`
- [ ] Tools for handling ambiguity
- [ ] Hierarchical documents
- [ ] Engineer individual components

### Framework

- [x] [Jun 13] Include views in the schema (some spider2 db has views instead of tables)
- [x] [Jun 13] Optimize schema fetching - approximate `num_unique` and `null_ratio`
- [x] [Jun 15] Tracing with [langfuse](https://langfuse.com/)
- [x] [Jun 20] Add `global_id` field  for db connectors for schema/metadata caching
- [x] [Jun 21] `toolhub` sub-package
- [x] [Jun 23] Support max steps
- [x] [Jul 16] Optimize evaluation - share execution results between metrics, record execution results
- [x] [Jul 22] HSchema viewing and statistics script
- [x] [Sep 22] ARCS data loader
- [x] [Sep 22] New schema.py with AmbigNL2QTask
- [x] [Sep 23] Rewrite metrics, pipelines
- [x] [Sep 24] Simple user simulator, simple qa disambiguation
- [x] [Sep 25] Rewrite usage and metrics storage, remove pydantic_ai_utils.py
- [x] [Sep 25] Rewrite metrics aggregation
- [x] [Sep 25] get_schema() and get_column_description() tools
- [x] [Sep 25] Initialize agent with config
- [x] [Sep 28] Registry for agents, datasets, metrics
- [x] [Sep 29] Replace HSchema with SchemaCompressor
- [x] ambig-flat
- [x] to_{readable, directory, summary}
- [x] Usage tracking
- [x] Trajectory
- [x] langfuse
- [x] User simulator - include_history
- [x] ambig-structured
- [x] Fix tool metrics
- [x] Make agent reusable across tasks using TaskRunContext
- [x] Refactor
- [x] Allow empty pred_query on exception
- [x] Run ambig-{simple, flat, structured} on full ARCS dataset
  - ambig-simple: 20.79 spider2_ex, 19.8 bird_sql_ex
  - ambig-flat: 17.82 spider2_ex, 14.85 bird_sql_ex
  - ambig-structured: 20.79 spider2_ex, 18.81 bird_sql_ex
- [x] Fix run_query timeout, set max concurrency to 4 and timeout to 120
- [x] Update README.md
- [x] Fix data format - gold query latency, sample values, parameter dtype
- [x] print_dataset_stats.py with ambiguity dataset metrics
- [x] LLMs
  - [x] Max concurrency limiting with ThrottledAgent
  - [x] OpenAI - chat vs. responses API
  - [x] batch size
  - [x] Anthropic
  - [x] Deepseek
  - [x] Gemini
  - [x] Qwen
  - [x] Llama
  - [x] Gemma (serverless not available)
  - [x] OpenAI OSS
  - [x] Kimi
- [x] Fix empty ambiguity points
- [x] print_run_stats.py, refactor print_dataset_stats.py
- [x] run sql for resolved only
- [x] Remove SQL from sqlalchemy errors
- [x] Avoid race condition in user simulator history with lock
- [x] Fix mypy errors
- [x] Fix schema compressor
- [x] Fix Gemini on run_query tool's `parameters` field
- [ ] Compare implementation of mintq, ambig-text2sql, bird-interact
- [x] Read BIRD-INTERACT paper and design experiments
- [ ] Support Ambrosia
- [ ] ambig_structured agent with partial ground-truth input
- [ ] Simple QA with user patience limit
- [ ] Task up sampling
- [ ] Metrics
- [ ] Fix Spider table and column names casing
- [ ] Metadata ablation
- [ ] Raise ModelRetry on too many interpretation combinations

## Misc

Interesting BIRD question IDs:
```
1126: State the name of players who came from Belgium.

944:  How much faster in percentage is the champion than the driver who finished the race last in the 2008 Australian Grand Prix?
```

```
npx @modelcontextprotocol/inspector \
  uv \
  --directory /zfs1/users/yanlin/projects/nl2q-rl \
  run \
  -m mintq.mcp \
  --dataset spider2-snow \
  --split dev \
  --database AIRLINES
```

### Starting initial postgres databases
```
docker run -d --name postgres_financial \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=financial \
  -p 5440:5432 \
  postgres

docker run -d --name postgres_github_repos \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=github_repos \
  -p 5441:5432 \
  postgres
```

#### Convert sqlite to postgres

```
pgloader \
  /home/yanlin/mintq/data/BIRD-SQL/dev_20240627/dev_databases/financial/financial.sqlite \
  postgresql://postgres:postgres@localhost:5440/financial

pgloader \
  /home/yanlin/github_repos_date.sqlite \
  postgresql://postgres:postgres@localhost:5441/github_repos
```

#### Dump the database to .sql file

```
pg_dump -h localhost -p 5440 -U postgres -d financial > financial.sql

pg_dump -h localhost -p 5441 -U postgres -d github_repos > github_repos.sql
```

#### Start a new postgres database from the .sql file

```
docker run -d --name postgres_financial \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=financial \
  -p 5440:5432 \
  -v /home/yanlin/financial.sql:/docker-entrypoint-initdb.d/financial.sql \
  postgres

docker run -d --name postgres_github_repos \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=github_repos \
  -p 5441:5432 \
  -v /home/yanlin/github_repos.sql:/docker-entrypoint-initdb.d/github_repos.sql \
  postgres
```