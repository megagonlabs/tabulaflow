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


- [ ] Update schema preprocessor - fix gas station price
- [ ] "rates and ratio not multiplied by 100" ignored by gpt-4.1
- [ ] Test GPT-5, gemini-3-flash/pro
- [ ] Model ensemble
- [ ] Caching for embedding models
- [ ] Fix schema linking evaluation / include FK columns
- [ ] Re-evaluate not_used
- [ ] get_table_schema for non-linked tables
- [ ] Table description (table profiler)
- [ ] min-max range for numeric columns
- [ ] Update extract_all_source_columns to support schema_name
- [ ] Show intermediate tables for CTE in run_query tool
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