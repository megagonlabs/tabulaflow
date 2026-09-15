# Benchmarks

| Benchmark | Task | Query system | Splits | Setup |
| --- | --- | --- | --- | --- |
| BIRD-SQL | Text-to-query | SQLite | `dev`, `dev_20251106`, `train` | Managed download |
| Spider 2.0 Snow | Text-to-query | Snowflake | `test` | Download and credentials |
| Spider 2.0 Lite | Text-to-query | BigQuery, Snowflake, SQLite | `test` | Download; credentials vary |
| Spider 2.0 dbt | Data transformation | dbt and DuckDB | `test` | Managed download |
| Beaver | Text-to-query | MySQL | `test` | Managed download and Docker runtime |
| ARCS | Ambiguous text-to-query | SQLite | `test`, `test_unsampled` | Manual dataset setup |
| AMBROSIA-S | Ambiguous text-to-query | SQLite | `test`, `few_shot_examples` | Managed download |
| CypherBench | Text-to-Cypher | Neo4j | `test`, `train` | Managed download and Docker runtime |

For CypherBench, select the [Cypher schema formatter](agents.md#configure-an-agent).

## Install benchmark data

List installation status and download a managed benchmark:

```bash
tabulaflow benchmark list
tabulaflow benchmark download bird-sql
```

Managed downloads are stored under TabulaFlow's benchmark directory and
validated before use. `download arcs` instead reports the local layout required
for its manually distributed data.

Beaver and CypherBench also provide managed database runtimes:

```bash
tabulaflow benchmark start beaver
tabulaflow benchmark stop beaver

tabulaflow benchmark start cypherbench
tabulaflow benchmark stop cypherbench
```

`start` downloads missing data before starting the service. CypherBench accepts
`--split train`; its default runtime serves the test split.

## Load a benchmark split

```python
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader

loader = BirdSQLDatasetLoader()
dataset = await loader.get_split_async(
    "dev",
    databases=["california_schools"],
    subsample_size=10,
)
```

`dataset.tasks` contains typed benchmark tasks. `dataset.db_connectors` maps
each selected database name to a live connector. See
[resource cleanup](running-experiments.md#release-resources) for closing them.

## Select tasks reproducibly

Use QIDs to select an exact task set:

```python
dataset = await loader.get_split_async("dev", qids=["3", "17", "42"])
```

QID filtering precedes sampling, which uses a fixed seed. Unknown QIDs,
unsupported splits, and oversized samples raise `ValueError`. Saved runs retain
the selected QIDs.

## Cloud credentials

Spider 2.0 Snow reads `SF_USER`, `SF_PASSWORD`, and `SF_ACCOUNT`, or accepts
credentials in its loader constructor. Spider 2.0 Lite uses the same Snowflake
settings and also supports BigQuery and local SQLite databases. BigQuery needs
a billing project (`GOOGLE_CLOUD_PROJECT`) and application-default credentials
or `GOOGLE_APPLICATION_CREDENTIALS`. Only the selected databases need credentials.

See the [loader reference](api/benchmarks.md#built-in-loaders) for constructor
options, including explicit data paths and connection settings.

For your own questions and databases, see
[adding a benchmark](extending.md#add-a-benchmark).
