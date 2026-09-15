# Benchmarks

Benchmark loaders provide questions, reference queries, database connectors,
and default evaluation metrics. Select tasks by split, database, QID, or a
deterministic sample.

## Choose a benchmark

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

BIRD-SQL is the clearest starting point for SQL experiments. Use ARCS or
AMBROSIA-S to study ambiguity, Spider 2.0 for enterprise databases and dbt, and
CypherBench for property graphs.

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

Construct a loader, then await `get_split_async(...)`:

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

QID filtering happens before deterministic sampling. Prefer explicit QIDs when
an experiment must use an exact task set:

```python
dataset = await loader.get_split_async("dev", qids=["3", "17", "42"])
```

Unknown QIDs, unsupported splits, and samples larger than the available task
set raise `ValueError`.

Sampling uses a fixed seed. Save the selected QIDs with your results so the
task set remains explicit even if the dataset's ordering or contents change.

## Benchmark requirements

### BIRD-SQL

The managed download includes the development and training questions, SQLite
databases, and column descriptions. Its default metrics include official and
soft execution accuracy, executability, prediction success, and schema-linking
diagnostics.

### Spider 2.0

Spider 2.0 Snow reads `SF_USER`, `SF_PASSWORD`, and `SF_ACCOUNT`, or accepts
credentials in its loader constructor. Spider 2.0 Lite uses the same Snowflake
settings and also supports BigQuery and local SQLite databases. BigQuery needs
a billing project (`GOOGLE_CLOUD_PROJECT`) and application-default credentials
or `GOOGLE_APPLICATION_CREDENTIALS`. Only the selected databases need credentials.

Spider 2.0 dbt evaluates generated dbt projects against local DuckDB results.
See the [loader reference](api/benchmarks.md#built-in-loaders) for constructor
options, including explicit data paths and connection settings.

### Beaver

Beaver downloads its task data and runs benchmark MySQL databases through
Docker. Start the runtime before loading the test split and stop it when the
experiment is complete.

### ARCS and AMBROSIA-S

Both benchmarks represent questions with multiple valid interpretations. ARCS
requires manual dataset placement; AMBROSIA-S has a managed download with local
SQLite databases. Use the ambiguity-aware agents described in
[Agents](agents.md#ambiguity-aware-agents).

### CypherBench

CypherBench evaluates text-to-Cypher over Neo4j property graphs. Its managed
runtime starts one set of Docker services for the selected split. Use the
`full_schema` agent with the [Cypher schema formatter](agents.md#configure-an-agent)
for a baseline.

For your own questions and databases, see
[adding a benchmark](extending.md#add-a-benchmark). Next,
[choose an agent](agents.md) compatible with your tasks.
