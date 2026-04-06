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

### ARCS

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
- [x] Compare implementation of mintq, ambig-text2sql, bird-interact
- [x] Read BIRD-INTERACT paper and design experiments
- [x] Simple QA with user patience limit
- [x] ambig_structured agent with partial ground-truth input
- [x] Metrics
  - [x] simple_ex
    - [x] Repetitions considered by default
  - [x] ambiguity point P/R/F1
  - [x] interpretation P/R/F1
    - [x] should be P/R/F1 conditioned on the ambiguity point is correct
  - [x] Handle tasks without finite ambiguity points for interpretation P/R/F1 -> null values
- [x] Support Ambrosia
- [x] Task up-sampling
- [x] Cost computation using litellm
- [x] Analyze exp90 simple vs. structured (info leakage in ambig_simple)
- [x] Fix parameter_values for ambig_flat and ambig_structured
- [x] Default ignore_repetitions = True for simple_ex
- [x] Fix sampling - sample from non-empty gold queries only
- [x] Fix user simulator
- [x] Patch LLM output parsing for `<tool_call>` tags
- [x] Replace demonstrations with trajectories
- [x] LLMs
  - [x] Fix Qwen3
  - [x] Fix Deepseek
- [x] Metrics
  - [x] Parameter ambig point P/R/F1
  - [x] Ambig point metrics for ambig_simple
  - [x] Ambig type ambig point P/R/F1
    - [x] Fix for ambig_simple
    - [x] Fix precision (if no pred, p is None instead of 0.0)
  - [x] perfect_disambiguation
- [x] Baselines
  - [x] No disambiguation
- [x] Fix annotation - all infinite ambiguity points should be semantic_value
- [x] Analyze 99_gpt-4.1_simple_patience_1 -> info leakage for overlapping ambiguity points
- [x] Fix user simulator info leakage - two stage approach
- [x] Support reasoning effort
- [x] User simulator - allow refusal for out-of-scope questions
  - [x] Two-stage user simulator
- [x] Dataset instructions
- [x] User effort
- [x] Ambig point index out-of-range
- [x] Disambiguation tools - get_schema
- [x] Categorical values for table with a small number of rows
- [x] Aggregated metrics registration
- [x] Support taxonomy
- [x] Fix user simulator - include all interpretations
- [x] Tune on Ambrosia
- [x] Ambrosia - dataset instructions
- [x] Debug ambrosia cost - simple vs. structured
- [x] Experiements for major claims
  - [x] Performance variance
  - [x] Performance scales w.r.t. reasoning effort
  - [x] Taxonomy-proof
  - [x] ARCS vs. Ambrosia
- [x] Error analysis metrics
  - [x] found_one
- [x] print_exps.py
- [x] Debug sonnet-4.5 vs. opus-4.5
- [x] Exps
  - [x] Main
    - [x] gemini-3
  - [x] Architecture
  - [x] Taxonomy
  - [x] Ambrosia
  - [x] User patience
  - [ ] No disambiguation
  - [ ] Gemini and Claude reasoning effort
- [x] Fix ambig_simple prompt when user patience is provided
- [x] Rename exp dirs
- [x] Rerun evaluate.py on all results

### MINTQ 0.9.0

Jan 9
- [x] Fix reasoning effort
- [x] Error analysis pipeline
- [x] "ambrosia_s" -> "ambrosia-s"
- [x] Support BIRD dev_20251106 split

Jan 12
- [x] Fix gold not executable
  - [x] BIRD dev_20240627
  - [x] BIRD dev_20251106
  - [x] BIRD train - many questions are unanswerable and queries refer to non-existent tables or columns
- [x] Metrics for each BIRD difficulty level
- [x] Tune instructions on return columns

Jan 13
- [x] Postprocessing module
  - [x] Parse question submodule
  - [x] Postprocess submodule
- [x] run_query tool with no parameters
- [x] Include exec results in pred query

Jan 14
- [x] Test postprocessor
  - [x] Exp 156: Performance goes from 0.58 to 0.48
    - Reason: gpt-5-mini-minimal outputs extra columns when parsing the question
    - Observation: gpt-5-mini with minimal reasoning does not work well but medium reasoning works well
- [x] Replace evidence field with question_instructions
- [x] Metric raw_pred_bird_sql_ex
- [x] analyze_postprocess_impact_async in analyze_errors.py
  - [x] improved and regressed tasks
  - [x] fixable regressed tasks
  - [x] potential improvable tasks
- [x] Reject postprocessed queries that is non-executable or adds columns

Jan 15 - Jan 16
- [x] Schema linking module
  - [x] SQL parsing utils
  - [x] Schema linking with gold query
  - [x] Schema linking with expanded gold query
  - [x] Schema linking with expanded pred query
  - [x] Improve SQL parsing coverage
  - [x] Add FKs when expanded to a different table -> keep all FKs for now
- [x] Schema linking metrics
- [x] Add field `extra_pred_info` to NL2QTaskOutput
- [x] Add param `db_connector` to metrics

Jan 20 - 21
- [x] Fix mypy errors
- [x] Support running on challenging subset
- [x] Update bird-sql instructions
  - [x] Do not concat to full name
  - [x] Do not transpose columns? 
- [x] Add schema_name to ColumnRef
- [x] Column description (column profiler)
  - [x] Concise description embedded in schema
  - [x] Detailed description using get_column_description tool

Jan 22
- [x] Update prompt - follow hints on conflict
- [x] sql_ddl schema formatter
- [x] Tune on thrombosis_prediction
- [x] Tune schema linking
  - [x] min_columns_for_schema_linking
  - [x] keep PK columns in schema linking

Jan 23
- [x] Refactor analyze_errors.py
- [x] Markdown format for readable output
  - [x] Markdown format for NL2QTaskOutput and NL2QTask
  - [x] Markdown format for Trajectory
  - [x] Markdown error analysis output with hyperlinks to task_readable.md
- [x] Refactor config.py

Jan 26
- [x] preprocessors subpackage
- [x] preprocess_and_cache.py
- [x] FK inference for database without FKs

Jan 27
- [x] Disable columns not useful
- [x] Improve FK inference and column profiler
  - [x] Rewrite prompt using xml tag syntax
  - [x] Skip FKs to the same target table

Jan 28
- [x] MINTQ_CACHE_REQUIRED=1
- [x] ERDiagramSynthesizer

Jan 29
- [x] ER diagram Mermaid formatter
- [x] export_readable_cache.py

Jan 30
- [x] Experiment 191: Direct ER diagram embedded: improve on moderate/challenging but hurts on simple
- [x] ER diagram linking, reduce schema linking size with ER diagram
- [x] Explicit "NULL" for NULLABLE columns
- [x] Experiment 192: Improved schema linking with ER diagram: no improvement to 191, linked_percentage 0.42->0.28, perfect_linked_schema_r 0.96 -> 0.93
- [x] Update system prompt borrowed from https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Cursor%20Prompts/Agent%20Prompt%202.0.txt
  - [x] Exp 193: run_query.num_calls.avg 1.09 -> 1.38, cost $24.9 -> $26.9
- [x] run_query tool: display number of rows
- [x] Analyze moderate and challenging first 5 tasks: most errors are due to ambiguity

Feb 2
- [x] Update BIRD instructions
  - [x] Rewrite format
  - [x] No Ties in Highest or Lowest Entity
  - [x] AND vs OR ambiguity
  - [x] Integer Division vs Decimal Division
- [x] Update sql_ddl formatter - add xml tags for comment parts
- [x] Exp 195: Improved bird instructions and sql_ddl formatter - no improvement
- [x] Update sql_agent prompt - handle ambiguity
  - [x] Exp 196: Ambiguity prompt - decreases performance by 1.6%
- [x] Sample rows in table
  - [x] Field `sampled_df` in SQLTableSchema
  - [x] sql_ddl formatter
  - [x] Update format_df
  - [x] Update `sampled_df` when trimming schema
- [x] diff_run.py

Feb 3
- [x] Exp 198: subsampled rows, integer division, format_df - slightly improve over 196
- [x] Exp 199: remove resolve_ambiguity prompt - improvement to 65.65
- [x] analyze_errors.py - support LLM classification using defined error categories

Feb 4 - 5
- [x] BaseDatasetPreprocessor
- [x] Support variable length tuples for caching
- [x] Upgrade pydantic-ai to 1.52.0
- [x] Few-shot examples for SQL generation
- [x] Few-shot examples for postprocessing
- [x] Small improvements
  - [x] xml syntax for all prompts
  - [x] order tables in schema to match ER diagram
- [x] Exp 203: few-shot examples - improved to 0.6656 raw_pred_bird_sql_ex
- [x] Analyze output/199_gpt-5-mini-medium/analysis.md
  - [x] YES / NO
    - sql_dev_20240627_469
    - sql_dev_20240627_473
  - [x] Column order
  - [x] Do not strictly follow - hints might have typo / incorrect formula
    - bird-sql_dev_20240627_1306
  - [ ] FK inconsistency (using each side give different results)
  - [ ] Exact column name not used (the other column in the FK used instead)
  - [ ] Removing NULL in results - need to investigate the net improvement
  - [ ] Postprocessing failure (mostly due to question parsing)
  - [ ] Nested queries over ORDER BY ... LIMIT 1
    - bird-sql_dev_20240627_837
  - [x] Empty results
    - bird-sql_dev_20240627_860
  - [x] Full name
    - bird-sql_dev_20240627_878
  - [x] Percentage
    - bird-sql_dev_20240627_881
  - [x] Truncated execution results
    - bird-sql_dev_20240627_929
  - [x] Return only one for top N questions
  - [x] Gold incorrect
    - bird-sql_dev_20240627_1026
    - bird-sql_dev_20240627_1028
    - bird-sql_dev_20240627_1085
    - bird-sql_dev_20240627_1144
    - bird-sql_dev_20240627_1174
    - bird-sql_dev_20240627_1297
    - bird-sql_dev_20240627_1520
  - [ ] preprocssed schema quality - gas station price is aggreageted price not unit price

Feb 9 - 10
- [x] Split a199
- [x] Fix rate limit
- [x] openai_service_tier
- [x] Fix reading cache every time
- [x] Fix a199 errors
  - [x] Update bird instructions

Feb 11
- [x] Exp 206: updated bird instructions
  - [x] Updated bird instructions with percentage value format - bird_sql_ex: 0.6623, simple_ex: 0.6943
- [x] Tune postprocessing module
  - [x] percentage value * 100 order (multiplied after numerator vs denominator)
  - [x] Column order
  - [x] Removing aliased column require modifying other clauses to keep the query executable
  - [x] printf returns string instead of float
    - bird-sql_dev_20240627_226
    - bird-sql_dev_20240627_227
    - bird-sql_dev_20240627_255

Feb 12 - 14
- [x] Exp 207: bird_sql_ex at 0.6734!
- [x] Spider 2.0
  - [x] Preprocessing - disable column profiler and foreign key predictor
  - [x] Rename evidence to document, include document in prompt
- [x] Fix schema linking
- [x] Fix extract_all_source_columns, disable passing schema
- [x] Fix name casing in sql_conn.py and column quoting in schema formatting

Feb 20
- [x] table_group_regexes
- [x] other_exec_results -> alternative_results
- [x] Patch spider2-snow eval

Feb 23
- [x] GA360 - decide how to handle date-partitioned tables
  - group_date_partitioned_tables and group_table_regexes
  - no num_rows, examples and sampled_df for skipped tables
- [x] Fix formatting for multi-line values (e.g. JSON)
  - [x] sampled_df formatting
  - [x] example values formatting
- [x] Look at PATENTSVIEW
  - [x] Observation: lots of classification code lookup tables in spider2
- [x] Fix invalid utf-8 for NOAA_DATA

Feb 25
- [x] Optimize schema fetching
  - [x] Speed up num_unique computation using table sampling
  - [x] Compute all column stats using table sampling for large tables
- [x] spider2-snow dataset instructions
- [x] Fix error message formatting

Feb 26
- [x] Fix bugs on spider2-snow
  - [x] table sampling on views
  - [x] snowflake fail to reflect warnings
  - [x] df serialization error for NaT values
  - [x] exclude AMAZON_VENDOR_ANALYTICS__SAMPLE_DATASET and NETHERLANDS_OPEN_MAP_DATA
  - [x] Cache overwriting
  - [x] schema compression infinite loop
  - [x] log level
  - [x] config options MINTQ_DATASET and MINTQ_SPLIT

Feb 27
- [x] Fix bugs on spider2-snow
  - [x] column_stats_mode, fix schema fetching
  - [x] column stats merging
  - [x] example values fetching
  - [x] _denorm
- [x] schema compression v2 - multiple patterns for one table

Feb 28
- [x] Improve schema compression
- [x] direct_prompting
- [x] get_table_schema tool
- [x] Fix query timeout: add option MINTQ_QUERY_TIMEOUT

March 1
- [x] Exp 214: direct_prompting on spider2-snow and bird-sql
  - spider2-snow: 0.2132 spider2_ex, executable: 0.5294
  - bird-sql: 0.6336 bird_sql_ex, executable: 0.9733
- [x] Tune Spider2 instructions
  - [x] Percentage values
  - [x] No ties in highest or lowest entity
- [x] Investigate output/test/readable/sf_local010/task_readable.md
- [x] Fix value formatting bug
- [x] Fix column order mismatch
- [x] Fix 81 - 88 batch evaluation slow: set DEFAULT_DF_MAX_ROWS to 10000
- [x] Fix df serialization error for bytes
- [x] mini_agent

March 2
- [x] Exp 217: mini_agent
  - mini_agent, 0.3915 spider2_ex, executable: 0.9706
  - mini_agent, 0.6408 bird_sql_ex, executable: 1.0000
- [x] Exp 218: new spider2 instructions
  - direct_prompting, 0.3162 spider2_ex, executable: 0.7261
- [x] query cache
  - [x] MINTQ_QUERY_CACHE_MODE
- [x] Fix evaluation - round-trip csv
- [x] Update df serialization to feather format
- [x] Fix bugs
  - [x] Duplicate column names
  - [x] Lone surrogates in string values
  - [x] Oversized Python ints

March 3
- [x] Exp 222: mini_agent with 40 steps: 0.5368 spider2_ex
- [x] Column description: https://github.com/xlang-ai/Spider2/blob/main/spider2-snow/resource/databases/NOAA_DATA/NOAA_GSOD/GSOD1929.json
- [x] Exp 223: mini_agent with column description:
  - spider2-snow: 0.5110 spider2_ex  cost: $16.13
  - bird-sql: 0.6551 bird_sql_ex
- [x] print_schema.py
- [x] config option formatter_max_total_columns and use_column_description
- [x] Separte cache config for schema and preprocessor
- [x] db_summarizer
- [x] Add dialect field to SQLSchema
- [x] mintq_agent
- [x] Revise spider2 instructions
  - [x] Schema-Qualified Table Names
  - [x] Case-Sensitive Identifiers

March 4
- [x] Exp 226: mintq_agent
  - spider2-snow: 0.5533 spider2_ex, cost: $11.6, steps: 5.5
  - bird-sql: 0.6447 bird_sql_ex, cost: $11.2, steps: 3.4
- [x] "step-by-step" CTE prompt
- [x] Exp 227: mintq_agent with step-by-step CTE prompt
  - spider2-snow: 0.5607 simple_ex, 0.5496 spider2_ex, cost: $12.6, steps: 5.8
- [x] Exp 228: mintq_agent with updated step-by-step CTE prompt
  - spider2-snow: 0.563 simple_ex, 0.5570 spider2_ex, cost: $15.0, steps: 7.0
- [x] Support compressed schema for tools
- [x] json_schema field
  - [x] json_schema field

March 5
- [x] Backfill json_schema field in cached schemas
- [x] json_schema formatter
  - [x] max_depth
  - [x] max_fields

March 6
- [x] Exp 233, 234: mintq_agent with get_json_schema, no improvement
- [x] Fix timeout still 90 seconds
- [x] read_only option for SQLConnector
- [x] get_table_schema tool: max_columns, column_regex_filter, offset, limit
- [x] revise run_query tool docstring - "returning large result sets is safe"

March 8
- [x] sf_bq416 (GOOG_BLOCKCHAIN)
  - [x] Snowflake blocks javascript UDF creation
- [x] GA360
- [x] Support running procedural blocks, use exec_driver_sql
- [x] Fix mypy

March 9
- [x] Exp 239 with procedural: no improvement
- [x] Exp 239: GPT-5: 0.6618 spider2_ex
- [x] Exp 240: Claude Opus 4.6: failed - rate limit exceeded
- [x] Analyze
  - [x] DELIVERY_CENTER
  - [x] GITHUB_REPOS
- [x] Update db summaries - use better llm
  - [x] db_summarizer prompt - title format, schema-qualified table names
- [x] Move language field from tasks to db connectors
- [x] Fix bytes not truncated bug
- [x] Update spider2 instructions
  - [x] rows to return
  - [x] always use double-quoted identifiers
- [x] Analyze full spider2-snow test split exp239

March 10
- [x] Exp 247 (spider2-snow test, updated instructions): gpt-5.4 simple_ex 0.6838, spider2_ex 0.6710, cost $391.50; gpt-5-mini simple_ex 0.5938, spider2_ex 0.5846, cost $16.19
- [x] Analyze spider2 rounding behavior - question explicitly specifies rounding
- [x] Top 10 costliest tasks
- [x] path parameter for get_json_schema - test on tasks that invoked get_json_schema
  - qids where get_json_schema was invoked: "sf_bq010 sf_bq001 sf_bq002 sf_bq003 sf_bq004 sf_bq008 sf_bq268 sf_bq270 sf_bq091 sf_bq033 sf_bq209 sf_bq027 sf_bq210 sf_bq212 sf_bq214 sf_bq127 sf_bq215 sf_bq036 sf_bq182 sf_bq248 sf_bq193 sf_bq255 sf_bq359 sf_bq291 sf_bq348 sf_bq253 sf_bq068 sf_bq092 sf_bq065 sf_bq063 sf_bq028 sf_bq090 sf_bq442 sf_bq102 sf_bq445 sf_bq103 sf_bq124 sf_bq366 sf_bq346 sf_bq421 sf_bq451 sf_bq452 sf_bq453 sf_bq412 sf_bq423 sf_bq070 sf_bq324 sf_ga001 sf_ga002 sf_ga007 sf_ga031 sf_ga032 sf_ga006 sf_ga009 sf_ga014 sf_ga012"
- [x] Model ensemble
  - [x] majority_ensembler
  - [x] ensemble.py
  - [x] llm_ensembler
  - [x] Exp 249 - 251
    - Exp 249 majority_ensembler: 5x_gpt-5-mini 0.6066, mixed 0.6728 spider2_ex
    - Exp 250 llm_ensembler (gpt-5-mini): 5x_gpt-5-mini 0.6140, mixed 0.6746 spider2_ex
    - Exp 251 llm_ensembler (gpt-5): 5x_gpt-5 0.6452, 5x_gpt-5_dedup 0.6526, mixed 0.7132, mixed_dedup 0.7040 spider2_ex
    - Observation:
      - Strong llm as ensembler is needed
      - llm_ensembler is much better than majority_ensembler (with strong llm)
      - improvements are ~5% - 8%

March 11
- [x] test whether null_ratio is useful - no improvement
- [x] Exp 253: claude-sonnet-4-5 (spider2-snow test): simple_ex 0.5827, spider2_ex 0.5735, cost $479.20
- [x] Exp 254: gpt-5.3-codex (spider2-snow test): simple_ex 0.7004, spider2_ex 0.6985, cost $92.15
- [x] Exp 255: agent_ensembler: 5x_gpt-5_dedup spider2_ex 0.6691, mixed_dedup spider2_ex 0.7132

March 16
- [x] Update spider2 instructions - safe to include extra columns
- [x] Exp 256: Test gemini-3-flash/pro
  - [x] gemini-3.1-pro-preview: simple_ex 0.6029, spider2_ex 0.5974, cost $401.26; gemini-3-flash-preview: simple_ex 0.5974, spider2_ex 0.5919, cost $68.53
- [x] Support spider2-lite

March 17
- [x] Cache spider2-lite schemas
  - [x] Fix cannot distinct
  - [x] Fix unqualified columns
  - [x] Fix json schema for struct and array columns
  - [x] Fix json stringification and mixed type columns
- [x] RealScoreAggregator
- [x] Fix mintq.__init__.py -> mintq.configure()

March 18
- [x] Exp 258: gpt-5.4-mini on spider2-snow: simple_ex 0.6232, spider2_ex 0.6158
- [ ] Exp 259: deepseek-v3p2 on spider2-snow
- [x] Cache spider2-lite schemas
- [x] Update python and litellm
- [x] Fix bigquery project name
- [x] Exp 261: gpt-5-mini on spider2-lite: simple_ex 0.5028, spider2_ex 0.4954, cost $15.37
- [x] Exp 263: gpt-5-mini on spider2-lite (fix project name): simple_ex 0.5875, spider2_ex 0.5820, cost $15.54
- [x] Exp 264: gpt-5.3-codex on spider2-lite: simple_ex 0.6869, spider2_ex 0.6796, cost $80.19
- [x] Fix bigquery auto tracing
- [x] Improve env var parsing
- [x] Fix asyncio lock shared across event loops
- [x] Fix mypy errors
- [x] Exp 266: new db summary: gpt-5.3-codex on spider2-lite: simple_ex 0.6851, spider2_ex 0.6740, cost $84.18

March 19 
- [x] dbt data loader
- [x] spider2_duckdb_match metric
- [x] dbt agent
  - [x] file_editor tool
  - [x] run_dbt tool

March 20
- [x] Support spider2-dbt
- [x] Fix bugs
  - [x] Fix gold db path mismatch
  - [x] Gold db missing - send email to Spider 2.0 authors
  - [x] Fix file_editor crash on binary file
  - [x] Fix dbt binary path
  - [x] Fix duckdb lock conflict
- [x] refresh_schema_async
- [x] get_table_schema with compress and refresh
  
March 21 - 22
- [x] Revise dbt agent
  - [x] schema refresh
  - [x] duckdb progress bar
  - [x] no color for dbt
  - [x] view count timeout
  - [x] per-line truncation
  - [x] always start from fresh copy
  - [x] view_range for viewing dirs
  - [x] dbt deps
  - [x] dbt instructions
    - [x] time-sensitive -> unsolvable
    - [x] keep data type
    - [x] ambiguity interpretation
- [x] Single class for run_query tool
- [x] Refactor metrics

March 23
- [x] execute_bash tool
- [x] dbt_llm_ensembler
- [x] Revise dbt agent


March 30
- [x] Support csv, excel, parquet files with SQLConnector.from_files_async
- [x] PropertyGraphSchema
- [x] Neo4jConnector

March 31
- [x] Support cypherbench
  - [x] cypherbench dataset loader
  - [x] cypherbench metrics
- [x] Fix mypy
- [x] DBRegistry

April 1
- [x] Registry tools

April 2
- [x] Refactor
- [x] registry_get_db_document tool
- [x] Support outputing multiple records

April 3
- [x] Refactor using textual

April 4
- [x] Polish UI
- [x] Fix streaming and record parsing
- [x] Fix disaplaying many tabs

Features
- [x] Data browser
- [ ] Query browser
- [ ] Copy to clipboard
- [ ] Session resume
- [ ] Semantic operator
- [ ] Data writing
- [ ] Web search

Release plan
- [ ] Run N candidates on spider2-snow and spider2-lite
- [ ] Support Neo4j and cypherbench
- [ ] Support CSV files and Excel files
- [ ] mintq-cli
- [ ] Support redis
- [ ] Support mongodb
- [ ] Documentation
- [ ] spider2-lite submission
- [ ] spider2-dbt submission
- [ ] spider2-snow submission
- [ ] Support DAComp
- [ ] Tuning on BIRD-SQL

- [ ] Rename db_connector to connectors?
- [ ] Use OpenAI plain text tool!!!
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

- [ ] Add column description during column expansion in sql_agent.py?
- [ ] Support official snowflake mcp: https://github.com/Snowflake-Labs/mcp
- [ ] Update schema preprocessor - fix gas station price
- [ ] Caching for embedding models
- [ ] Fix schema linking evaluation / include FK columns
- [ ] Re-evaluate not_used
- [ ] get_table_schema for non-linked tables
- [ ] Table description (table profiler)
- [ ] min-max range for numeric columns
- [ ] Update extract_all_source_columns to support schema_name
- [ ] Remove unuseful FKs in linked schema
- [ ] gpt-5-mini for sql gen and gpt-4.1 for postprocessing
- [ ] Fix Spider table and column names casing
- [ ] Read CHESS source code
- [ ] Support LSH index
- [ ] Include db schema in postprocessing?
- [ ] Spider 2.0 custom data
- [ ] Incorporate changes from blue-delibird (e.g. lock per event loop)
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

```bash
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


```python
async def main():
    db_connector = await SQLConnector.from_url_async(
        "sqlite+aiosqlite://test.db",
        # postgres+asyncpg://localhost:5432/test
        # snowflake://...
        # duckdb://...
    )
    db_connector.schema  # A SQLSchema object

    await db_connector.run_query_async("SELECT ...", parameters, timeout=120)
```
```python
from pydantic_ai import Agent

class MyText2SQLAgent:
    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput:
        schema_str = self.formatter.format(db_connector.schema)
        agent = Agent(
            model="gpt-4.1",
            instructions=f"Translate to a SQL query. Database schema: {schema_str}",
            tools=[
                run_query_tool.as_pydantic_ai_tool(),
                get_table_schema_tool.as_pydantic_ai_tool()
            ]
        )
        result = await agent.run(task.question)
        sql_query = result.output
        return SimpleNL2QTaskOutput(pred_query=PredQuery(query=sql_query))
```