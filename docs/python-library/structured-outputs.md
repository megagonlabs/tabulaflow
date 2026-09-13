# Structured outputs

Work with an agent's results as data, not just text. Tables, charts, maps, and
graphs have structured specifications that your application can inspect,
serialize, and render. You can also construct outputs without an agent.

## Switch between revenue and profit

This example gives a table and chart the same parameterized data source.
Changing the metric resolves a different query; switching back reuses the
stored result. No API key is needed.

```python title="structured_outputs.py"
--8<-- "examples/structured_outputs.py"
```

Revenue is **East: $1,500, West: $2,000**; profit is **East: $450, West: $400**.
The printed result IDs are `R1`, `R2`, then `R1` again. Both artifacts share
each resolved result. The script prints data and specifications, not a chart window.

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/structured_outputs.py
```

## How resolution works

- `OutputSpec` declares artifacts, their sources, and optional parameters.
- `OutputStore` holds query results and metadata. Fixed sources point to a
  stored result; parameterized sources execute on demand and cache results
  by selection. Declaring a source does not execute its query.
- `OutputResolver` turns a specification and selection into artifacts with
  their data attached. Your application supplies selections and renders the result.

Here, `metric` accepts only the two declared column names. Query templates
render text; they are not SQL bind parameters. Keep templates under application
control and use validated choices rather than inserting unchecked input.

## Use outputs from a session

A completed turn provides the same declaration in `result.output`. Use
`OutputResolver(session.output_store)` to resolve it. To fetch a single table
or chart's data and query metadata, call
`session.output_store.resolve_artifact_source(artifact.source_id)`.

`UnavailableArtifact` identifies an artifact that could not resolve; other
artifacts can still be usable. Invalid selections raise `OutputResolutionError`
instead.

Serializing `OutputSpec` saves the declaration, not the underlying DataFrames
or live connectors. Keep the store and any needed connectors available for
later resolution. Cached parameterized results are reused, not automatically
refreshed when a database changes.

Explore [output specifications](api/output.md#output-specifications),
[result storage](api/output.md#result-storage), and
[text formatting](api/output.md#formatting) for the full APIs.
