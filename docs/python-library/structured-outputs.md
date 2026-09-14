# Structured outputs

Work with an agent's results as data, not just text. Tables, charts, maps, and
graphs have structured specifications that your application can inspect,
serialize, and render. Their data can resolve on demand as parameter selections
change. Use outputs from a chat session or construct them without an agent.

## Example: Warehouse transfer graph

Explore monthly warehouse transfers as a table and a relationship graph, both
backed by the same SQLite query. A minimum-units parameter filters both
artifacts. No graph database is needed.

```python title="structured_outputs.py"
--8<-- "examples/structured_outputs.py"
```

At **100 units**, three routes appear. At **300**, only Chicago to Dallas
(500 units) and Dallas to Austin (350 units) remain. Returning to 100 reuses
the first result: the printed result IDs are `R1`, `R2`, then `R1` again.

`GraphArtifactSpec` maps the SQL result's origin and destination columns to
nodes and directed edges, with units as edge labels. The script prints the
selection, SQL, DataFrame, graph nodes and edges, and output specification.
It does not open a graph viewer or slider.

Run the example without a database server or API key:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/structured_outputs.py
```

## Resolve data on demand

- `OutputSpec` declares artifacts, their sources, and optional parameters.
- `OutputStore` holds query results and metadata. Fixed sources point to a
  stored result; parameterized sources execute on demand and cache results
  by selection. Declaring a source does not execute its query.
- `OutputResolver` turns a specification and selection into artifacts with
  their data attached. Your application supplies selections and renders the result.

`UnavailableArtifact` identifies an artifact whose data or specification could
not be resolved; other artifacts can still be usable. Invalid selections raise
`OutputResolutionError` instead.

## Add interactive controls

`NumberParameter` defines a range, step, and default. Here, `min_units` accepts
0 to 500 in steps of 50. TabulaFlow's data agent renders numeric parameters as
sliders; your own frontend can use the same definition for a slider or numeric
input and pass the selected value to the resolver.

Changing a parameter resolves the shared data once for both artifacts, without
another model call. The example changes values in Python to show this behavior
without a frontend. Use `ChoiceParameter` for a fixed set of options, such as
revenue versus profit. See [parameters and selections](api/output.md#parameters-and-selections).

Query templates render text; they are not SQL bind parameters. Keep templates
under application control and use validated parameters rather than unchecked
input.

## Use outputs from a session

A completed turn provides the same declaration in `result.output`. Use
`await OutputResolver(session.output_store).resolve(result.output, selection)`
to resolve it, where `selection` maps parameter names to values. Omit it to
use defaults. To fetch a single table or chart's data and query metadata, use
`await session.output_store.resolve_artifact_source(artifact.source_id, selection)`.

Serializing `OutputSpec` saves the specification, not the underlying DataFrames
or live connectors. Keep the store and any needed connectors available for
later resolution. Cached parameterized results are reused, not automatically
refreshed when a database changes.

Explore [output specifications](api/output.md#output-specifications),
[result storage](api/output.md#result-storage), and
[text formatting](api/output.md#formatting) for the full APIs.
