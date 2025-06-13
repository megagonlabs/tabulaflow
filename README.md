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

Roadmap:
- [x] SQL Agent starting with table names and foreign keys
- [ ] Hierarchical schemas
- [ ] Code diff tool
- [ ] Schema linking agent + SQL writing agent
- [ ] Hierarchical documents
- [ ] Engineer individual components
```
1126
944
```



Old prompt:

```
Translate the following natural language question into a SQLite query.
- The query must follow the database schema.
- You must use the hints to generate the query.
- The final answer must be the query rather than the result of the query.
- To connect multiple tables, you must use JOIN on one of the pairs in the 【Foreign keys】 section in the database schema.
  -  Keep in mind that the records in the tables may not perfectly align: the some entities in one table might not be covered by another table.
- When submitting the final query, remove any additional columns that are not required by the question.
  - If there are multiple columns that cover similar information, only include the one that is the most relevant and precise.
    - For example, if the question asks for only the list of events, only include the event ids without the dates.
    - For example, if the question asks for only the country and there are city, country, location, zipcode columns, only include the country column.
  - For example, if the question only ask for the highest score but not the name of the student, do not include the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not his score, do not include the score.
  - Example:
    Table: student
    [
    (id:TEXT, Primary Key, Example: 1),
    (name:TEXT, Examples: [John]),
    (readScore:INTEGER, Examples: [100, 95, 90]),
    (writeScore:INTEGER, Examples: [100, 95, 90]),
    (streetAddress:TEXT, Examples: ["123 Main St", "456 Maple Ave"]),
    (city:TEXT, Examples: ["Anytown", "Anycity"]),
    ]
    Question: What is the highest score in reading?
    Query: SELECT MAX(readScore) FROM student
    Question: What is the student with the highest score in reading?
    Query: SELECT name FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
    Question: What is the address of the student with the highest score in reading?
    Query: SELECT streetAddress FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
- DO NOT decompose the question into sub-questions, and use the intermediate results of previous queries to construct the final query
  - All logic of previous queries for sub-questions must be included in the final query.
  - However, you can debug a query by testing smaller components.
  - THIS IS NOT ALLOWED:
    * Question: What is the writing score of the student with the highest reading score?
    * Query 1: SELECT MAX(readScore) FROM student
    * Observation 1: 97
    * Final Query (NOT ALLOWED): SELECT writeScore FROM student WHERE readScore = 97
    The correct query should be: SELECT writeScore FROM student WHERE readScore = (SELECT MAX(readScore) FROM student)
- For non-digit text columns, always use the `search_keywords` tool to search for the keyword and ensure it exists in the database.
  - Try to search over all possible relevant columns across the database. Try to be very comprehensive.
  - Similarly, include potential synonyms in the keyword list.
- Before submitting the final query as answer, always use the `check_final_answer` tool to validate the query.

=== Your Task ===

Database Schema:
【DB_ID】 california_schools
【Schema】
# Table: satscores
[
(cds:TEXT, Primary Key, Examples: [10101080000000, 10101080109991, 10101080111682]),
(rtype:TEXT, Examples: [D, S]),
(sname:TEXT, Examples: [FAME Public Charter]),
(dname:TEXT, Examples: [Alameda County Office of Education]),
(cname:TEXT, Examples: [Alameda, Amador, Butte]),
(enroll12:INTEGER, Examples: [398, 62, 75]),
(NumTstTakr:INTEGER, Examples: [88, 17, 71]),
(AvgScrRead:INTEGER, Examples: [418, 503, 397]),
(AvgScrMath:INTEGER, Examples: [418, 546, 387]),
(AvgScrWrite:INTEGER, Examples: [417, 505, 395]),
(NumGE1500:INTEGER, Examples: [14, 9, 5])
]
# Table: schools
[
(CDSCode:TEXT, Primary Key, Examples: [01100170000000, 01100170109835, 01100170112607]),
(NCESDist:TEXT, Examples: [0691051, 0600002, 0600003]),
(NCESSchool:TEXT, Examples: [10546, 10947, 12283]),
(StatusType:TEXT, Examples: [Active, Closed, Merged]),
(County:TEXT, Examples: [Alameda, Alpine, Amador]),
(District:TEXT),
(School:TEXT, Examples: [FAME Public Charter]),
(Street:TEXT, Examples: [313 West Winton Avenue]),
(StreetAbr:TEXT, Examples: [313 West Winton Ave.]),
(City:TEXT, Examples: [Hayward, Newark, Oakland]),
(Zip:TEXT, Examples: [94544-1136, 94560-5359, 94612-3355]),
(State:TEXT, Examples: [CA]),
(MailStreet:TEXT, Examples: [313 West Winton Avenue]),
(MailStrAbr:TEXT, Examples: [313 West Winton Ave.]),
(MailCity:TEXT, Examples: [Hayward, Newark, Oakland]),
(MailZip:TEXT, Examples: [94544-1136, 94560-5359, 94612]),
(MailState:TEXT, Examples: [CA]),
(Phone:TEXT, Examples: [(510) 887-0152, (510) 596-8901, (510) 686-4131]),
(Ext:TEXT, Examples: [130, 1240, 1200]),
(Website:TEXT, Examples: [www.acoe.org]),
(OpenDate:DATE, Examples: [2005-08-29]),
(ClosedDate:DATE, Examples: [2015-07-31]),
(Charter:INTEGER, Examples: [1, 0]),
(CharterNum:TEXT, Examples: [0728, 0811, 1049]),
(FundingType:TEXT, Examples: [Directly funded]),
(DOC:TEXT, Examples: [00, 31, 34]),
(DOCType:TEXT, Examples: [County Office of Education (COE)]),
(SOC:TEXT, Examples: [65, 66, 60]),
(SOCType:TEXT, Examples: [K-12 Schools (Public)]),
(EdOpsCode:TEXT, Examples: [TRAD, JUV, COMM]),
(EdOpsName:TEXT, Examples: [Traditional]),
(EILCode:TEXT, Examples: [ELEMHIGH, HS, ELEM]),
(EILName:TEXT, Examples: [Elementary-High Combination]),
(GSoffered:TEXT, Examples: [K-12, 9-12, K-8]),
(GSserved:TEXT, Examples: [K-12, 9-12, K-7]),
(Virtual:TEXT, Examples: [P, N, F]),
(Magnet:INTEGER, Examples: [0, 1]),
(Latitude:REAL, Examples: [37.658212, 37.521436, 37.80452]),
(Longitude:REAL, Examples: [-122.09713, -121.99391, -122.26815]),
(AdmFName1:TEXT, Examples: [L Karen, Laura, Clifford]),
(AdmLName1:TEXT, Examples: [Monroe, Robell, Thompson]),
(AdmEmail1:TEXT),
(AdmFName2:TEXT, Examples: [Sau-Lim (Lance), Jennifer, Annalisa]),
(AdmLName2:TEXT, Examples: [Tsang, Koelling, Moore]),
(AdmEmail2:TEXT),
(AdmFName3:TEXT, Examples: [Drew, Irma, Vickie]),
(AdmLName3:TEXT, Examples: [Sarratore, Munoz, Chang]),
(AdmEmail3:TEXT),
(LastUpdate:DATE, Examples: [2015-06-23])
]
# Table: frpm
[
(CDSCode:TEXT, Primary Key, Examples: [01100170109835, 01100170112607, 01100170118489]),
("Academic Year":TEXT, Examples: [2014-2015]),
("County Code":TEXT, Examples: [01, 02, 03]),
("District Code":INTEGER, Examples: [10017, 31609, 31617]),
("School Code":TEXT, Examples: [0109835, 0112607, 0118489]),
("County Name":TEXT, Examples: [Alameda, Alpine, Amador]),
("District Name":TEXT),
("School Name":TEXT, Examples: [FAME Public Charter]),
("District Type":TEXT, Examples: [County Office of Education (COE)]),
("School Type":TEXT, Examples: [K-12 Schools (Public)]),
("Educational Option Type":TEXT, Examples: [Traditional]),
("NSLP Provision Status":TEXT, Examples: [Breakfast Provision 2]),
("Charter School (Y/N)":INTEGER, Examples: [1, 0]),
("Charter School Number":TEXT, Examples: [0728, 0811, 1049]),
("Charter Funding Type":TEXT, Examples: [Directly funded]),
(IRC:INTEGER, Examples: [1, 0]),
("Low Grade":TEXT, Examples: [K, 9, 1]),
("High Grade":TEXT, Examples: [12, 8, 5]),
("Enrollment (K-12)":REAL, Examples: [1087.0, 395.0, 244.0]),
("Free Meal Count (K-12)":REAL, Examples: [565.0, 186.0, 134.0]),
("Percent (%) Eligible Free (K-12)":REAL, Examples: [0.519779208831647, 0.470886075949367, 0.549180327868853]),
("FRPM Count (K-12)":REAL, Examples: [715.0, 186.0, 175.0]),
("Percent (%) Eligible FRPM (K-12)":REAL, Examples: [0.657773689052438, 0.470886075949367, 0.717213114754098]),
("Enrollment (Ages 5-17)":REAL, Examples: [1070.0, 376.0, 230.0]),
("Free Meal Count (Ages 5-17)":REAL, Examples: [553.0, 182.0, 128.0]),
("Percent (%) Eligible Free (Ages 5-17)":REAL, Examples: [0.516822429906542, 0.484042553191489, 0.556521739130435]),
("FRPM Count (Ages 5-17)":REAL, Examples: [702.0, 182.0, 168.0]),
("Percent (%) Eligible FRPM (Ages 5-17)":REAL, Examples: [0.65607476635514, 0.484042553191489, 0.730434782608696]),
("2013-14 CALPADS Fall 1 Certification Status":INTEGER, Examples: [1])
]
【Foreign keys】
satscores.cds=schools.CDSCode
frpm.CDSCode=schools.CDSCode


Question: Please list the lowest three eligible free rates for students aged 5-17 in continuation schools.

Hints:
Eligible free rates for students aged 5-17 = `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)`

SQLite Query:
```