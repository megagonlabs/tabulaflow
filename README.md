# mintq

A **Min**imalist **T**ext-to-**Q**uery Toolkit

Contact: yanlin@megagon.ai

Project structure:
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

## Dataset setup

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
