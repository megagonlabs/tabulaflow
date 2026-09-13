# Working with data

Use connectors to inspect schemas and query SQL databases, Neo4j, and SPARQL
endpoints directly, without an agent or model call.

If you've used [LiteLLM](https://docs.litellm.ai/docs/) or
[Pydantic AI](https://pydantic.dev/docs/ai/models/overview/) to work with different model providers,
TabulaFlow brings a similar approach to databases: a unified async interface
with structured schemas and query results. Queries stay in SQL, Cypher, or
SPARQL, so LLMs can draw on their existing training rather than learn a new
query language.

For SQL databases, the same awaited API works with both sync and async drivers.
Schema inspection gives you tables, columns, relationships, and sample values
in a consistent structure across SQL backends.

## Example: Find products to restock

This example creates a small inventory database in memory, inspects its schema,
and calculates how many units are needed to reach each product's reorder point.

```python title="working_with_data.py"
--8<-- "examples/working_with_data.py"
```

The result contains **8 HDMI cables** and **7 USB-C docks**. `result.df` is a
DataFrame you can process directly; `format_dataframe(...)` turns it into text.
`SQLDDLSchemaFormatter` does the same for the schema, ready for inspection or
an LLM prompt.

The example round-trips the result through JSON, including its DataFrame and
execution metadata. TabulaFlow's `SerializableDataFrame` also preserves nested
JSON values, binary data, and decimals, without custom encoders or flattening
complex columns.

Check `result.error` before using the result. A successful statement can have
no DataFrame, for example when creating a table. Connection setup and DataFrame
writes can raise exceptions directly; the example closes its connector in
`finally` even when something fails.

Run the example without a database server or API key:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/working_with_data.py
```

## Connect your own data

- Use `SQLConnector.from_url_async(...)`, `Neo4jConnector.from_url_async(...)`,
  or `SPARQLConnector.from_url_async(...)` when you know the backend.
- Use `connect_data_source(source, display_name="Inventory")` for a local file,
  a dataset URL, or a named catalog entry. Files and Hugging Face datasets are
  loaded into DuckDB, so you can inspect and query them through the same SQL
  connector interface.
- Add live connectors to a `DataConnectorRegistry` to make multiple sources
  available to an agent. Names such as `stock` let the agent select a source
  for each query.

See [opening sources](api/data.md#opening-sources) and
[file and dataset loaders](api/data.md#file-and-dataset-loaders) for options.

## Control query execution

`SQLConnector` also handles execution controls that would otherwise need
backend-specific code:

- **Timeouts and cancellation.** Set a deadline with
  `run_query_async(..., timeout=30)` or cancel the awaiting task. On supported
  dialects, these stop the running database query. Timeouts appear in
  `result.error`; task cancellation propagates as `asyncio.CancelledError`.
- **Concurrency and result limits.** Configure how many queries can run at
  once and how many rows a result can contain. Share a `dbms_semaphore` across
  SQL connectors to cap concurrent queries to the same warehouse.
- **Optional caching.** Cache SQL schemas and query results to avoid repeated
  work. Both caches are off by default; enable them when reusing a snapshot is
  appropriate. Refresh the schema on demand with `refresh_schema_async()`.
- **Read-only guard.** The default `read_only=True` helps prevent accidental
  writes. Use read-only database credentials for enforced access control.
  The example enables writes only to load its sample data.

See [connector configuration](api/data.md#configuration) for settings and
defaults. Execution controls vary by backend.

Next: [use a connector in a chat session](chat-sessions.md), or implement the
[DataConnector protocol](api/data.md#connector-interface) for your own backend.
