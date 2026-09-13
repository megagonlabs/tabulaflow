# Working with data

Use connectors to inspect schemas and query SQL databases, Neo4j, and SPARQL
endpoints directly, without an agent or model call.

If you've used [LiteLLM](https://docs.litellm.ai/docs/) or
[Pydantic AI](https://pydantic.dev/docs/ai/models/overview/) to work with different model providers,
TabulaFlow brings a similar approach to databases: a unified async interface
with structured schemas and query results. Queries stay in SQL, Cypher, or
SPARQL, so LLMs can draw on their existing training rather than learn a new
query language.

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

Run the example without a database server or API key:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/working_with_data.py
```

## Connect your own data

- Use `SQLConnector.from_url_async(...)`, `Neo4jConnector.from_url_async(...)`,
  or `SPARQLConnector.from_url_async(...)` when you know the backend.
- Use `connect_data_source(source, display_name="Inventory")` for a local file,
  a dataset URL, or a named catalog entry. It loads or connects the source and
  returns a queryable connector.
- Add live connectors to a `DataConnectorRegistry` to make multiple sources
  available to an agent. Aliases such as `stock` identify sources within that
  registry; they do not rename the database.

See [opening sources](api/data.md#opening-sources) and
[file and dataset loaders](api/data.md#file-and-dataset-loaders) for options.

## Handle results and connections

Check `ExecResult.error` before using a query result. A successful statement
can have no DataFrame, for example when creating a table. Connection setup and
DataFrame writes can raise exceptions directly.

The example enables writes only to load its sample data. For existing SQL
databases, keep the default `read_only=True` and use database credentials with
appropriate permissions. Close connectors in `finally`, as above.

Next: [use a connector in a chat session](chat-sessions.md), or implement the
[DataConnector protocol](api/data.md#connector-interface) for your own backend.
