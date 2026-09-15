# Data connectors

Query SQL databases, Neo4j, SPARQL endpoints, files, and datasets through a
common async interface. Each connector provides a structured schema and query
results while keeping its backend's query language.

## Example: Find products to restock

Create an inventory database from a DataFrame:

```python
--8<-- "examples/working_with_data.py:data-imports"

--8<-- "examples/working_with_data.py:connect"
--8<-- "examples/working_with_data.py:sample-data"
```

Query it and read the result as a DataFrame:

```python
--8<-- "examples/working_with_data.py:query"
```

??? example-output no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-inventory.txt"
    ```

Schema discovery includes columns, relationships, and sample values. Format
that schema for an LLM prompt or inspection:

```python
--8<-- "examples/working_with_data.py:format-imports"

--8<-- "examples/working_with_data.py:schema"
```

Save and restore the result, including its DataFrame and execution metadata:

```python
--8<-- "examples/working_with_data.py:result-imports"

--8<-- "examples/working_with_data.py:serialize"
```

Run the complete example without a database server or API key:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/working_with_data.py
```

Close the connector with `await stock.close_async()` when finished. The script
includes cleanup even if an operation fails.

## Connect your own data

Open an existing CSV, Parquet file, dataset URL, or database connection URL:

```python
from tabulaflow.data import connect_data_source

inventory = await connect_data_source("inventory.csv", display_name="Inventory")
print(inventory.schema)
```

Files and Hugging Face datasets become queryable DuckDB tables. Use
`SQLConnector`, `Neo4jConnector`, or `SPARQLConnector` directly for backend-specific
options. See [opening sources](api/data.md#opening-sources).

## Control query execution

Set execution limits when opening a database:

```python
from tabulaflow.data import SQLConnector, SQLConnectorConfig

config = SQLConnectorConfig(
    query_timeout_seconds=30,
    max_query_concurrency=4,
    max_result_rows=10_000,
)
database = await SQLConnector.from_url_async(
    "sqlite+aiosqlite:///inventory.sqlite", config=config
)
```

Connections default to read-only mode; the example enables writes to load data.
Schema and query caching are off by default. See [connector configuration](api/data.md#configuration)
for cache policies and backend-specific behavior.
