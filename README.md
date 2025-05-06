# mintq

A **Min**imalist **T**ext-to-**Q**uery Toolkit

Contact: yanlin@megagon.ai

Project structure:
```
mintq
├── baseline/               # text-to-query methods
│   ├── simple_zero_shot.py
│   ├── tool_agent.py
│   └── ...
├── dataset/                # text-to-query datasets
│   ├── bird-sql/
│   ├── spider2-snow/
│   └── ...
├── db_connector/           # database connectors
│   ├── sqlite_conn.py
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
├── run_baseline.py         # entry point to run the baseline methods
└── evaluate.py             # script to evaluate the results
```
