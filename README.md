# mintq

A **Min**imalist **T**ext-to-**Q**uery Toolkit that offers:

📐 **Structured Data**: All data—including database schemas—is structured and explicitly [defined](mintq/schema.py). No more dealing with complex black-box dictionaries or parsing massive schema strings.

🔍 **Type-safe**: Every method is type-hinted and checked with static type checker mypy.

🧩 **Modular**: Core components like [database connectors](mintq/db_connector/base.py), [dataloaders](mintq/datahub/base.py), [models](mintq/modelhub/base.py), [metrics](mintq/metric/base.py) follow the interfaces defined in the base.py files.

🔌 **Extensible**: Intefaces are designed to be minimal and flexible, without heavy abstractions. You are free to use any agent library to build your own text-to-query model.

🌐 **Multi-DBMS**: Works with a wide variety of databases including all SQL databases supported by sqlalchemy as well as graph databases like Neo4j.

🧠 **Built for Researchers**: Includes out-of-the-box support for popular research datasets like BIRD-SQL, Beaver, and Spider 2.0, including equivalent re-implementation of their official leaderboard metrics. Designed for efficient experimentation with:
- Multi-threaded inference and evaluation
- Trajectory tracing
- Agent tool call and token usage tracking

## 🚀 Quick Start

```python
from mintq.modelhub.simple_zero_shot import SimpleZeroShotNL2Q
from mintq.datahub.bird_sql import BirdSQLDatasetLoader
from mintq.schema_formatter import SQLDefaultSchemaFormatter
from mintq.metric import BirdSQLEx
from mintq.run_model import run_model
from mintq.evaluate import evaluate

# define the model factory function
# the `run_model` function below constructs a separate model instance for each sample to avoid race condition
def model_fn():  
    return SimpleZeroShotNL2Q(
        llm="openai/gpt-4o-mini",
        schema_formatter=SQLDefaultSchemaFormatter()
    )

dataloader = BirdSQLDatasetLoader(directory="data/BIRD-SQL")
dataset = dataloader.get_split("dev")  # dataset includes the text-to-query tasks and the database connectors
dataset.tasks = dataset.tasks[:3]

# run the model on the dataset using multi-threading
result = run_model(model_fn=model_fn, dataset=dataset, batch_size=10)
print(result.tasks[0].pred_query)

# evaluate execution accuracy
metrics = [BirdSQLEx()]
result_with_metrics = evaluate(result, dataset, metrics, num_threads=8)
print(result_with_metrics.aggregated_metrics)
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

---

Contact: yanlin@megagon.ai