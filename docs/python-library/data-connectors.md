# Data connectors

Query SQL databases, Neo4j, SPARQL endpoints, files, and datasets through a
common async interface. Each connector provides a structured schema and query
results while keeping its backend's query language.

## Example: Find products to restock

You're preparing a stock order. Find products below their reorder points and
calculate how many units to buy.

```python
--8<-- "tabulaflow/examples/working_with_data.py:data-imports"

--8<-- "tabulaflow/examples/working_with_data.py:connect"
--8<-- "tabulaflow/examples/working_with_data.py:sample-data"
```

Query it and read the result as a DataFrame:

```python
--8<-- "tabulaflow/examples/working_with_data.py:query"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-inventory.txt"
    ```

Schema discovery includes columns, relationships, and sample values. Format
that schema for an LLM prompt or inspection:

```python
--8<-- "tabulaflow/examples/working_with_data.py:format-imports"

--8<-- "tabulaflow/examples/working_with_data.py:schema"
```

??? example-details no-copy "Sample output"

    ````text
    --8<-- "examples/results/library-inventory-schema.txt"
    ````

Save and restore the result, including its DataFrame and execution metadata:

```python
--8<-- "tabulaflow/examples/working_with_data.py:result-imports"

--8<-- "tabulaflow/examples/working_with_data.py:serialize"
```

After [installing TabulaFlow](quick-start.md#try-it-yourself), run the complete
example without a database server or API key:

```bash
uv run tabulaflow examples run working-with-data
```

Connectors are async context managers, so `async with stock:` guarantees cleanup
even if an operation fails. You can also close one directly with
`await stock.close_async()`.

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
