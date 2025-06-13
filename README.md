# mintq

A **Min**imalist **T**ext-to-**Q**uery Toolkit that offers:

📐 **Structured Data**: All data—including database schemas—is structured and explicitly [defined](mintq/schema.py). No more dealing with complex black-box dictionaries or parsing massive schema strings.

🔍 **Type-safe**: Every method is type-hinted and checked with static type checker mypy.

🧩 **Modular**: Core components like [database connectors](mintq/db_connector/base.py), [dataloaders](mintq/datahub/base.py), [models](mintq/modelhub/base.py), [metrics](mintq/metric/base.py) follow the interfaces defined in the base.py files.

🔌 **Extensible**: Intefaces are designed to be minimal and flexible, without heavy abstractions. You are free to use any agent library to build your own text-to-query model.

🌐 **Multi-DBMS**: Works with a wide variety of databases including all SQL databases supported by sqlalchemy as well as graph databases like Neo4j.

🧠 **Built for Researchers**: Includes out-of-the-box support for popular research datasets like BIRD-SQL, Beaver, and Spider 2.0, including equivalent re-implementation of their official leaderboard metrics. Designed for efficient experimentation with:
- Concurrent inference and evaluation with asyncio
- Trajectory tracing
- Agent tool call and token usage tracking

## 🚀 Quick Start

```python
import asyncio
from mintq.modelhub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.datahub.bird_sql import BirdSQLDatasetLoader
from mintq.schema_formatter import SQLDefaultSchemaFormatter
from mintq.metric import BirdSQLEx
from mintq.run_model import run_model_async
from mintq.evaluate import evaluate_async


async def main():
    dataloader = BirdSQLDatasetLoader(directory="data/BIRD-SQL")
    # dataset includes the text-to-query tasks and the database connectors
    dataset = await dataloader.get_split_async("dev")  
    dataset.tasks = dataset.tasks[:3]

    # define the model arguments
    # the `run_model` function below uses this to construct a separate model instance for each sample to avoid race condition
    model_args = {"llm": "openai/gpt-4o-mini", "schema_formatter": SQLDefaultSchemaFormatter()}
    # run the model on the dataset using async coroutines
    result = await run_model_async(SimpleZeroShotNL2Q, model_args, dataset=dataset, batch_size=8)
    print(result.tasks[0].pred_query)
    # SELECT MAX("Percent (%) Eligible Free (K-12)")
    # FROM frpm
    # WHERE "County Name" = 'Alameda';

    # evaluate execution accuracy
    metrics = [BirdSQLEx()]
    result_with_metrics = await evaluate_async(result, dataset, metrics, batch_size=8)
    print(result_with_metrics.aggregated_metrics)
    # {'avg_latency_seconds': 1.472, 'avg_api_calls': 1.0, 'total_api_calls': 3, 'avg_input_tokens': 2490.6667, 'total_input_tokens': 7472, 'avg_output_tokens': 49.3333, 'total_output_tokens': 148, 'avg_api_cost_usd': 0.0004, 'total_api_cost_usd': 0.0012, 'avg_steps': 1.0, 'bird_sql_ex': 0.3333}


if __name__ == "__main__":
    asyncio.run(main())
```

We also provide the [run_model.py](mintq/run_model.py) and [evaluate.py](mintq/evaluate.py) scripts for convenience:

```bash
uv run mintq/run_model.py --model simple_zero_shot --dataset bird-sql --llm openai/gpt-4o-mini --result_dir output/test/ --debug
uv run mintq/evaluate.py --result_json output/test/result.json
```

## Project Structure

```
mintq
├── modelhub/               # text-to-query methods
│   ├── simple_zero_shot.py
│   ├── sql_agent_table_names_only.py
│   └── ...
├── datahub/                # text-to-query datasets
│   ├── bird_sql.py
│   ├── spider2.py
│   ├── beaver.py
│   └── ...
├── db_connector/           # database connectors
│   ├── sql_conn.py
│   ├── snowflake_conn.py
│   └── ...
├── metric/                 # evaluation metrics
│   ├── bird_sql_ex.py
│   ├── executable.py
│   └── ...
├── metadata_synthesizer/   # metadata generation methods
│   ├── er_diagram.py       # ER diagram inference
│   └── ...
├── schema_formatter/       # database schema formatters
│   ├── sql.py
│   └── ...
├── schema.py               # data structures used in the project
├── utils.py                # utility functions
├── run_model.py            # entry point to run the text-to-query methods
├── evaluate.py             # script to evaluate the results
└── visualization.py        # visualization utilities
```

## 📚 Dataset Setup

Currently, the following datasets are supported:

| Dataset | Key | Splits |
|---------|-----|------------------|
| BIRD-SQL | `bird-sql` | `train`, `dev` |
| Spider 2.0-snow | `spider2-snow` | `dev`|
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

- [x] SQL Agent starting with table names and foreign keys, with tools `list_columns`, `search_keywords`, `run_query`
- [ ] Hierarchical schemas
  - [x] HSchema generation v1
  - [x] HSchema generation v2
  - [ ] HSchema formatting
  - [ ] Design tools
- [ ] Reproduce previous performance
- [ ] Code diff tool
- [ ] Schema linking agent + SQL writing agent
- [ ] Hierarchical documents
- [ ] Engineer individual components

### Framework

- [ ] Include views in the schema (some spider2 db has views instead of tables)
- [ ] Metadata ablation
- [ ] Optimize evaluation (share execution results between metrics)

```
1126
944
```


