# `render_graph` bug with `CALL db.schema.visualization()` results

## Summary

`render_graph` fails when given the raw result of Neo4j `CALL db.schema.visualization()` through the `subgraph` mode, even though the procedure returns valid Neo4j node and relationship objects.

Path-based Cypher results render correctly. The failure is specific to result sets that contain bare Neo4j relationship objects rather than paths.

## Reproduction

Run this Cypher query:

```cypher
CALL db.schema.visualization()
```

This returns one row with two columns:
- `nodes`: a list of Neo4j node objects
- `relationships`: a list of Neo4j relationship objects

Then attempt to render it with:

```json
{"title":"Schema visualization","subgraph":[{"source_id":"Q17","caption":"title"}]}
```

Observed error:

```text
(error: subgraph[0] did not contain any Neo4j relationships or paths)
```

## Expected behavior

`render_graph` should recognize the Neo4j relationships in the `relationships` list, extract nodes and edges, and render the schema graph.

## Actual behavior

The renderer walks the result cells, recognizes Neo4j nodes and paths, but skips bare Neo4j relationship objects from `db.schema.visualization()`. As a result, no edges are extracted and the tool fails.

## Root cause

In `tabulaflow/toolhub/render_graph.py`, `_extract_subgraph_source()` uses exact class-name matching when deciding whether a value is a Neo4j relationship:

```python
if class_name == "Relationship" and hasattr(value, "start_node"):
    add_relationship(value)
    return
```

This is too strict for the Neo4j Python driver.

Neo4j relationship instances are often dynamic subclasses whose class name is the relationship type itself, not the literal string `"Relationship"`.

For example, the Neo4j driver creates relationship classes like this:

```python
def relationship_type(self, name: str) -> type[Relationship]:
    return type(str(name), (Relationship,), {})
```

So relationship objects may have class names such as:
- `RATED`
- `ACTED_IN`
- `DIRECTED`
- `IN_GENRE`

These are still valid Neo4j relationship objects, but the current renderer rejects them because it checks `type(value).__name__ == "Relationship"`.

## Why path queries still work

Path results succeed because the renderer separately recognizes `Path` objects:

```python
if class_name == "Path" and hasattr(value, "nodes") and hasattr(value, "relationships"):
    for node in value.nodes:
        add_node(node)
    for rel in value.relationships:
        add_relationship(rel)
    return
```

Once inside a recognized path, `add_relationship()` handles the relationship objects correctly. The bug is only in the top-level detection of bare relationship objects.

## Suggested fix

Replace the exact class-name check with subclass-safe or duck-typed detection.

For example, instead of:

```python
if class_name == "Relationship" and hasattr(value, "start_node"):
```

use something more permissive, such as checking for the required Neo4j relationship attributes:

```python
if hasattr(value, "start_node") and hasattr(value, "end_node") and hasattr(value, "type"):
    add_relationship(value)
    return
```

Similarly, node/path detection should prefer capability-based checks over exact class-name matching where possible.

## Impact

This affects any Cypher result consumed through `render_graph.subgraph` where relationships are returned directly rather than wrapped inside paths. `CALL db.schema.visualization()` is a clear reproduction case.

## Workaround

Reshape the schema procedure output into explicit node and edge tables and use column-based `nodes` + `edges` graph specs instead of `subgraph` mode.

For example:

```cypher
CALL db.schema.visualization() YIELD nodes, relationships
UNWIND relationships AS r
RETURN startNode(r).name AS source, type(r) AS rel_type, endNode(r).name AS target
```

and separately:

```cypher
CALL db.schema.visualization() YIELD nodes, relationships
UNWIND nodes AS n
WITH DISTINCT properties(n)['name'] AS name
RETURN name AS id, name AS label, name AS group
```

Then render using standard column-mode `nodes` and `edges`.
