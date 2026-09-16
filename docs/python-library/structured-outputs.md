# Structured outputs

Work with tables, charts, maps, and graphs as typed specifications with query
provenance. Resolve their data on demand, either from an agent's response or
from specifications you create yourself.

## Use outputs from a session

After `result = await session.run(...)`, resolve the returned artifacts and
inspect their data and queries:

```python
from tabulaflow.output.resolver import (
    OutputResolver,
    ResolvedChartArtifact,
    ResolvedTableArtifact,
    UnavailableArtifact,
)

resolved = await OutputResolver(session.output_store).resolve(result.output)
for artifact in resolved.artifacts:
    if isinstance(artifact, UnavailableArtifact):
        print("Unavailable:", artifact.artifact_id, artifact.reason)
    elif isinstance(artifact, (ResolvedTableArtifact, ResolvedChartArtifact)):
        print("Artifact:", artifact.label)
        print("Source:", artifact.result.metadata.connector_alias)
        print("SQL:", artifact.result.metadata.query)
        print("DataFrame:\n", artifact.result.df)
```

Chart artifacts also expose their Vega-Lite specification as `artifact.spec`.
Your frontend can render the resolved artifacts directly.

## Example: Warehouse transfer graph

You're reviewing transfers between warehouses. Explore the transfers as an
interactive graph without using a graph database, with a filter for the minimum
transfer size.

??? example-details "Create the sample database"

    ```python
    --8<-- "examples/structured_outputs.py:data-imports"

    --8<-- "examples/structured_outputs.py:connect"
    --8<-- "examples/structured_outputs.py:registry"
    --8<-- "examples/structured_outputs.py:sample-data"
    ```

```python
--8<-- "examples/structured_outputs.py:store-imports"

--8<-- "examples/structured_outputs.py:store"
```

## Add interactive controls

Declare a minimum transfer size and a query that uses it. Creating the source
does not execute the query:

```python
--8<-- "examples/structured_outputs.py:parameter-imports"

--8<-- "examples/structured_outputs.py:source"
```

`NumberParameter` provides the bounds and default for a slider or numeric input.
Use `ChoiceParameter` for a fixed set of options. See
[parameters and selections](api/output.md#parameters-and-selections).

## Resolve data on demand

Share the source between a table and a graph. Origin and destination values
become graph nodes; each transfer becomes a directed edge:

```python
--8<-- "examples/structured_outputs.py:artifact-imports"

--8<-- "examples/structured_outputs.py:artifacts"
```

Change the selection without another model call. Both artifacts share one
query result, and returning to an earlier selection reuses that result:

```python
--8<-- "examples/structured_outputs.py:resolve-imports"

--8<-- "examples/structured_outputs.py:resolve"
```

??? example-details no-copy "Sample output"

    ```text
    --8<-- "examples/results/library-transfers.txt"
    ```

Run the complete example without a database server or API key:

```bash
uv run https://megagonlabs.github.io/tabulaflow/examples/structured_outputs.py
```

The script prints data and graph structure and closes its connector. See
[result storage](api/output.md#result-storage) for persistence and cache behavior.
