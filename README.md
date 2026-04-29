# mintq-cli

## Installation (for developers)

```bash
git clone git@github.com:megagon-internal/mintq.git
cd mintq
uv venv
make sync
```

## Quick Start


```bash
export OPENAI_API_KEY=...  # not needed if you are only browsing data
uv run mintq
```

Use `/connect` to connect to a data source (Huggingface datasets, local csv/excel files, SQL databases, etc.), then either run `/browse` to manually browse the data or say "Analyze" to have LLM analyze the data.

## Utility Commands (for developers)

We use `make` to manage a few common commands we frequently use (see [`Makefile`](Makefile) for their definitions):

```bash
make format          # format and lint
make mypy            # type check with mypy
make sync            # sync the dependencies in pyproject.toml into the venv (e.g. when others have updated the dependencies)
make last-trajectory # print the path to the last trajectory of mintq-cli agent
```

## Use Cases

- Chatting to SQL databases
- Chatting to local files (csv, excel, json, …)
- Chatting to built-in public data sources (Huggingface, FRED, Wikidata …)
  - "Analyze the query template distribution of CypherBench"
  - "GDP and unemployment rates in the last 5 quarters"
- Data manipulation
  - "Transform this dataset to the OpenAI finetuning format"
- Building data from web (covers all functionalities of Blue-delibird)
  - "Find all data agent benchmarks in 2025"
  - "List all popular scuba diving destinations and the flight prices from SFO on July 1st."
- Support semantic operators (handles all data questions that Blue can handle)
  - "Tag questions that are ambiguous where both pred and gold are valid in results_gpt5.json"
  - "Tune the prompt for 5 iterations on this dataset"
  - "Translate this dataset into English and Chinese"
- Labeling data
  - "Label 10 samples" -> Manual review -> "Label all data"
- Supports cross-data-source querying
  - "What is the difference of GITHUB_REPOS and GITHUB_REPOS_DATE?"
- Supports outputting multiple tables
  - "Analyze this dataset" → distribution of domains, question complexity, ground-truth

Most useful for the lab:
- Data analysis, visualization and manipulation
- Error analysis of model predictions
- Literature survey

Partially replaces:
- Partially replaces DBeaver for data browsing
- Replaces current open-source text-to-SQL agents: Chat2DB, PandasAI, DataBao
- Partially replaces Jupyter Notebook workflows for data analysis and visualization
- Partially replaces OpenAI Deep Research agents on challenging data building tasks


## TODOs

[old worklog](backup/README_Apr20_2026.md)

April 20
- [x] Switch to parquet for df serialization
- [x] Query history with persistence to workspace DuckDB
- [x] key_columns in run_subagent tool

April 21
- [x] Json loading
- [x] Fix error on concurrent DDLs
- [x] Improve data browsing
  - [x] Live browsing
  - [x] Error on preview loading
- [x] Improve run_subagent tool
  - [x] sql_filter for filtering
  - [x] Write trajectory and error metadata to each row
  - [x] Prompt tuning use case - direct mode
  - [x] Use sqlalchemy statement

April 22
- [x] Result preview UI

April 23
- [x] Result preview UI
- [x] Ctrl+C
- [x] Cancellation for sql_conn.py

April 24
- [ ] Refactor sql_conn.py
  - [x] Use subprocess for loaders
  - [x] from_files_async to loaders/
  - [x] Test for the bug
  - [x] UI bug, spinner with error
  - [x] Cancellation for write_dataframe_async and run_query_async

April 27
- [x] Refactor sql_conn.py
  - [x] Combine timeout and cancellation handling
  - [x] remove aiosqlite path
  - [x] Cancellation for all sql dialects, sync and async
  - [x] Check ThrottledEngine API, whether engine used externally
  - [x] Access sql_conn.py and refactor
  - [x] Documentation for sql_conn.py
- [x] Fix huggingface readme fetching

April 28
- [x] Submitted issue on duckdb for https://huggingface.co/datasets/stellalisy/HorizonBench
- [x] "Enter Inspect" aligned to the right
- [x] Pydantic AI partial trajectory on interrupt
- [x] Fix missing record label
- [x] Fix scroll on column sorting
- [x] Fix first column suppressed
- [x] Copy to input box
- [x] Ambrosia use case
- [ ] Run sub agent - show num instead of percentage
- [ ] Fix "plan first" ignored
- [ ] Pass instructions to subagent
- [ ] Web search

- General
  - [ ] Improve transfer_record?
  - [ ] /reconnect
  - [ ] Copy to clipboard
  - [ ] Session resume
  - [ ] Semantic join - cross join
  - [ ] Data export
  - [ ] Support interrupting preview loading
  - [ ] Support interrupting agent
  - [ ] Pass db doc on connect for small dbs?
  - [ ] Multimodal data processing in subagent
  - [ ] Disable compression for small dbs?
  - [ ] Enriched with other data in huggingface repo
  - [ ] Show query latency
- Data/Cell/Query Browser
  - [ ] Support multi-modal data browsing (images, audio, video, etc.)
  - [ ] Query browser - show language and database
  - [ ] Refresh for get_column_json_schema and get_db_document
  - [ ] Pagination for cell browser
  - [ ] /export
  - [ ] /import with auto LLM import
- Delibird
  - [ ] Building from web
  - [ ] Building from files
- Visualization
  - [ ] Open visualization in browser
  - [ ] Map visualization
- Scenarios
  - [ ] Data browsing (replace DBeaver)
  - [ ] Multi-source querying on databases
    - [ ] Compare two similar databases
    - [ ] Profile all 152 spider2-snow databases
  - [ ] Public data sources
    - [ ] Huggingface, analyze, preprocessing (replace jupyter notebook)
    - [ ] Wikidata
    - [ ] Government/academic data
  - [ ] Error analysis
  - [ ] Running inference
  - [ ] Semantic operators
  - [ ] Web deep research (replace aisheets)
- Study other open-source projects
  - [ ] Claude code - tool description in system prompt or tool schema?
  - [ ] OpenClaw


---

===== BELOW IS OUTDATED =====

===== BELOW IS OUTDATED =====

===== BELOW IS OUTDATED =====

---

# mintq

**Min**imalist **T**ext-to-**Q**uery Library

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
    config = BasicAgentConfig(llm="openai:gpt-4.1-mini", schema_formatter="sql_basic")
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
│   ├── spider2_snow.py
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

Unzip the archive and move its contents into `data/ambrosia-s/`:

```bash
unzip data.zip && mv data data/ambrosia-s/ambrosia
```

Next, download the structured disambiguation annotations from Google Drive:

```bash
uvx gdown "https://drive.google.com/uc?id=1Zqx4sVuQGWZuyuT91OY3tnARC6Tz6EQp" -O data/ambrosia-s/ambrosia_few_shot_examples.json
uvx gdown "https://drive.google.com/uc?id=1cYftWIdRQfOVaHSVuSjOA4XjfcOvodk2" -O data/ambrosia-s/ambrosia_test.json
```

Finally, run the following scripts to add question texts and gold queries to the annotations:

```bash
uv run python scripts/ambrosia-s/add_values_to_annotations.py --csv data/ambrosia-s/ambrosia/ambrosia.csv --input data/ambrosia-s/ambrosia_few_shot_examples.json --output data/ambrosia-s/ambrosia_few_shot_examples_processed.json
uv run python scripts/ambrosia-s/add_values_to_annotations.py --csv data/ambrosia-s/ambrosia/ambrosia.csv --input data/ambrosia-s/ambrosia_test.json --output data/ambrosia-s/ambrosia_test_processed.json
```

```
data/ambrosia-s
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




## TODOs

- [ ] Rename db_connector to connectors?
- [ ] Try OpenAI plain text tool?
- [ ] Analyze spider2-snow:
  - unfinished period like the current year to a finished one
  - If the identifier name itself contains a double quote, escape it by using **two double quotes**. To query a table named `Client"Data`, write: `SELECT * FROM "Client""Data"`
- [ ] bash tool for dbt agent
- [ ] Answer asking for number but instead pred query returns separate rows - analyze trivial errors
- [ ] Randomization for ensembling
- [ ] Update spider2-lite instructions
  - [ ] Quoting identifiers for snowflake?
  - [ ] Check not executable queries (both spider2-snow and spider2-lite)
- [ ] Revise db_summarizer prompt - "used for efficient navigation and SQL writing by SQL experts"
- [ ] schema linking for mintq_agent
- [ ] Code edit tool for editting complex queries
- [ ] non-empty ratio
- [ ] partial trajectories on error
- [ ] column descriptions all used

- [ ] ARCS
  - [ ] "lengthen over-specified questions" in intro (emphasize that questions in existing benchmarks are too long)
  - [ ] Section on ease of use in paper and website
  - [ ] Rationale for multiple resolution sampling - prevent LLM from guessing
  - [ ] Data sheet
  - [ ] Remove `extra_info` in ARCS data
  - [ ] Update website layout with top bar
  - [ ] Set schema formatter to sql_basic in scripts
  - [ ] Include example ambiguity in BIRD-SQL to showcase importance
    - bird-sql_dev_20240627_87

### Release test

- [ ] Remove cache
- [ ] Schema caching
- [ ] all gold queries executable
- [ ] Test ARCS
- [ ] Test BIRD
- [ ] Test Spider 2.0


---

Contact: yanlin@megagon.ai

---
