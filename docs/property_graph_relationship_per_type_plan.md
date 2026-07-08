# PropertyGraphSchema: relationship-per-type — Implementation Plan

Change `PropertyGraphSchema` to model relationships **once per relationship
type**, carrying an explicit list of connectivity endpoints, instead of one
`RelationshipSchema` per `(label, source_label, target_label)` triple.

> **Status:** proposed. Self-contained — implement top to bottom.

---

## 1. Motivation

Today `RelationshipSchema` is keyed per **(label, source, target)** triple
(`core/types.py:71`). This picks the *per-pattern* granularity for **both**
facts a relationship carries, but those two facts live at different granularities
in a property graph:

1. **Connectivity** — *which* `(:A)-[:R]->(:B)` patterns exist. Genuinely
   **per-triple**: one type `R` can connect several endpoint pairs.
2. **Properties + semantics** — *what fields* `R` carries and *what it means*. In
   Neo4j this is **per-type, globally** — a relationship type has a single
   property set; you cannot make `ACTED_IN` carry different properties depending
   on endpoints.

Because the current model attaches properties per-pattern, the per-type property
set gets **denormalized on build and re-normalized on format** — a pointless
round trip through the wrong key:

- `neo4j_conn._build_schema` fans each type's properties (from
  `db.schema.relTypeProperties()`, which is per-type) out onto *every* pattern
  sharing the type (`neo4j_conn.py:297-299`).
- `CypherSchemaFormatter._format_relationship_properties` then **dedups them back
  by label**, with the comment "multiple patterns may share a label"
  (`cypher.py:66-79`).

The Neo4j-standard Text2Cypher rendering we emit already splits these into two
sections — `The relationships:` (per-pattern lines) and `Relationship
properties:` (per-type lines). That split is itself evidence that the natural
decomposition is **per-pattern connectivity + per-type properties**. Aligning the
data model with it deletes both the fan-out and the dedup.

## 2. Key Decisions

- **One `RelationshipSchema` per type.** `label` becomes the identity. `properties`
  and `description` attach once (they are per-type facts). Connectivity moves to a
  new `endpoints: list[RelationshipEndpoint]`.
- **`endpoints` is a named model, not `tuple[str, str]`.** A
  `RelationshipEndpoint(source_label, target_label)` keeps the existing
  `source_label` / `target_label` field names, so every string interpolation in
  the formatter and UI reads the same (`ep.source_label`), avoids `ep[0]`/`ep[1]`
  ordering bugs, and is pydantic-native for the cached JSON. This is clarity, not
  abstraction — no behavior, just two named strings.
- **Neo4j-faithful, not universal.** This matches Neo4j (our only property-graph
  backend, and cypherbench's target) and the Text2Cypher rendering. It is
  deliberately *not* the right model for TigerGraph-style systems where an edge
  type's identity *includes* its endpoint pair. Nothing in the repo needs that
  today; revisit only if such a backend is added.
- **Replace the unused filter helper.** `get_relationships(label, source, target)`
  has **no callers**. Replace it with a per-type lookup plus a pattern iterator,
  rather than preserving a dead signature.

## 3. New data model (`core/types.py`)

Replace the current `RelationshipSchema` (`core/types.py:71-78`) and the
`PropertyGraphSchema` helpers (`:89-111`) with:

```python
class RelationshipEndpoint(BaseModel):
    """One (source, target) connectivity pattern for a relationship type."""

    source_label: str
    target_label: str


class RelationshipSchema(BaseModel):
    """Schema for one relationship type and all node patterns it connects."""

    label: str
    endpoints: list[RelationshipEndpoint] = Field(default_factory=list)
    description: str | None = None
    properties: list[GraphPropertySchema] = Field(default_factory=list)


class PropertyGraphSchema(BaseModel):
    """Property-graph schema usable with any graph database."""

    name: str
    description: str | None = None
    nodes: list[NodeSchema] = Field(default_factory=list)
    relationships: list[RelationshipSchema] = Field(default_factory=list)

    def get_node(self, label: str) -> NodeSchema:
        for n in self.nodes:
            if n.label == label:
                return n
        raise ValueError(f"Node type {label!r} not found.")

    def get_relationship(self, label: str) -> RelationshipSchema:
        for r in self.relationships:
            if r.label == label:
                return r
        raise ValueError(f"Relationship type {label!r} not found.")

    def iter_patterns(self) -> "Iterator[tuple[str, str, str]]":
        """Yield ``(label, source_label, target_label)`` for every endpoint."""
        for r in self.relationships:
            for ep in r.endpoints:
                yield (r.label, ep.source_label, ep.target_label)
```

Add `from collections.abc import Iterator` (or `from typing import Iterator`) to
the imports if not already present. Re-export `RelationshipEndpoint` from
`core/__init__.py` alongside `RelationshipSchema` (check the existing export
block; `RelationshipSchema`/`NodeSchema`/`GraphPropertySchema` are already
re-exported).

## 4. Build side (`core/db_connector/neo4j_conn.py:245-308`)

Rewrite `_build_schema` so relationships key on type and collect endpoints, and
properties attach once. Replace the `rels: dict[tuple[str, str, str], ...]` block
and the property fan-out.

Target logic:

```python
async def _build_schema(self) -> PropertyGraphSchema:
    nodes: dict[str, NodeSchema] = {}
    rels: dict[str, RelationshipSchema] = {}          # keyed by rel type

    # ... node labels + node properties unchanged (lines 249-270) ...

    for record in await self._run_cypher(_REL_PATTERNS_QUERY):
        source: str = record["source"]
        rel_type: str = record["type"]
        target: str = record["target"]
        rel = rels.setdefault(rel_type, RelationshipSchema(label=rel_type))
        endpoint = RelationshipEndpoint(source_label=source, target_label=target)
        if endpoint not in rel.endpoints:
            rel.endpoints.append(endpoint)
        for lbl in (source, target):
            if lbl not in nodes:
                nodes[lbl] = NodeSchema(label=lbl)

    rel_prop_seen: dict[str, set[str]] = {}
    for record in await self._run_cypher(_REL_TYPE_PROPERTIES_QUERY):
        if record["propertyName"] is None:
            continue
        rel_types = _parse_type_labels(record["relType"])
        prop_name = record["propertyName"]
        prop_types = record["propertyTypes"] or []
        dtype = prop_types[0] if prop_types else "UNKNOWN"
        for rel_type in rel_types:
            # A rel type can appear in relTypeProperties without a live pattern.
            rel = rels.setdefault(rel_type, RelationshipSchema(label=rel_type))
            seen = rel_prop_seen.setdefault(rel_type, set())
            if prop_name in seen:
                continue
            seen.add(prop_name)
            rel.properties.append(GraphPropertySchema(name=prop_name, dtype=dtype))

    sorted_nodes = sorted(nodes.values(), key=lambda n: n.label)
    for rel in rels.values():
        rel.endpoints.sort(key=lambda e: (e.source_label, e.target_label))
    sorted_rels = sorted(rels.values(), key=lambda r: r.label)

    return PropertyGraphSchema(
        name=self._schema_name,
        nodes=sorted_nodes,
        relationships=sorted_rels,
    )
```

Notes:
- The old inner loop `for key, rel in rels.items(): if key[0] == rel_type` (the
  fan-out, `:297-299`) is gone — properties attach directly to the single per-type
  entry.
- Import `RelationshipEndpoint` from `tabulaflow.core.types` at the top of the
  file (the existing import block already pulls `RelationshipSchema`,
  `neo4j_conn.py:18-19`).
- Node-collection and node-property loops (`:249-270`) are unchanged.

## 5. Format side (`core/formatters/cypher.py`)

The two-section output is now a direct read — no dedup.

- `format` (`:31-50`): change `rel_lines` to iterate patterns and
  `rel_prop_lines` to iterate types:

  ```python
  node_lines = [self.format_node(n) for n in schema.nodes]
  rel_lines = [
      self.format_pattern(rel.label, ep.source_label, ep.target_label)
      for rel in schema.relationships
      for ep in rel.endpoints
  ]
  rel_prop_lines = self._format_relationship_properties(schema.relationships)
  ```

- Replace `format_relationship(self, rel)` (`:60-61`) with:

  ```python
  def format_pattern(self, label: str, source_label: str, target_label: str) -> str:
      return f"(:{source_label})-[:{label}]->(:{target_label})"
  ```

- Replace `_format_relationship_properties` (`:66-80`) — drop the `seen` dedup set
  entirely, since there is now one entry per label:

  ```python
  def _format_relationship_properties(self, relationships: list[RelationshipSchema]) -> list[str]:
      lines: list[str] = []
      for rel in relationships:
          if not (rel.properties or rel.description):
              continue
          line = rel.label
          if rel.properties:
              line += " {" + ", ".join(self.format_property(p) for p in rel.properties) + "}"
          if rel.description:
              line += f"  // {rel.description}"
          lines.append(line)
      return lines
  ```

Output text is unchanged for existing graphs (same lines, same order) — this is
pure internal simplification. The docstring example (`:13-27`) stays valid.

## 6. UI side (`app/screens.py:1360-1393`)

The schema-browser tree currently renders one node per pattern. Keep that visual
by iterating endpoints, but the group count now reflects **types**.

- Group `status_text` (`:1374`): change `"{len(schema.relationships):,} relationship patterns"` to
  count patterns explicitly so the number is stable:

  ```python
  pattern_count = sum(len(r.endpoints) for r in schema.relationships)
  # ... status_text=f"{alias} > Relationships  |  {pattern_count:,} relationship patterns"
  ```

- The per-relationship loop (`:1378-1393`): iterate one tree node **per
  (type, endpoint)** so labels and the `_add_graph_properties` call are unchanged:

  ```python
  patterns = sorted(
      (
          (rel, ep)
          for rel in schema.relationships
          for ep in rel.endpoints
      ),
      key=lambda re: (re[0].label, re[1].source_label, re[1].target_label),
  )
  for rel, ep in patterns:
      rel_path = ("relationships", rel.label, ep.source_label, ep.target_label)
      rel_node = relationships.add(
          Text.assemble(rel.label, (f"  {ep.source_label} -> {ep.target_label}", "dim")),
          data=_NodeData(
              kind=_NODE_KIND_GRAPH_RELATIONSHIP,
              alias=alias,
              path=(alias, *rel_path),
              status_text=(
                  f"{alias} > Relationships > {rel.label}  |  "
                  f"{ep.source_label} -> {ep.target_label}  |  {len(rel.properties):,} properties"
              ),
          ),
          expand=self._expand_for((alias, *rel_path), False),
      )
      self._add_graph_properties(rel_node, alias, rel_path, rel.properties)
  ```

  A type with N endpoints now shows N sibling nodes that repeat its property set —
  acceptable and consistent with the old per-pattern tree. (Optional future
  refinement: collapse to one node per type with endpoints as a sub-group. Out of
  scope here.)

- The `Relationships  N` count leaf (grep for where `_graph_count_label` /
  `"Relationships"` count is built near `:1360`): decide whether the count should
  be **types** or **patterns**. Keep it **types** (`len(schema.relationships)`) so
  it matches "one entry per type"; the test asserts `"Relationships  1"` which
  holds either way for the single-type fixture. Confirm against the actual count
  expression when editing.

## 7. Tests

- `tests/test_schema_browser_graph.py:38-45`: update the fixture construction to
  the new shape:

  ```python
  relationships=[
      RelationshipSchema(
          label="ACTED_IN",
          endpoints=[RelationshipEndpoint(source_label="Person", target_label="Movie")],
          properties=[GraphPropertySchema(name="roles", dtype="LIST OF STRING")],
      )
  ],
  ```

  Add `RelationshipEndpoint` to the imports (`:8-14`). The existing assertions
  (`:90-96`) — including `"ACTED_IN  Person -> Movie"` and `"Relationships  1"` —
  should remain green unchanged; if `"Relationships  1"` was asserting a pattern
  count that you switched to types, it still equals 1 here.

- Add a **multi-endpoint** regression test (new or extend existing) that proves
  the win: one type with two endpoint pairs, formatted via `CypherSchemaFormatter`,
  yields **two** pattern lines under `The relationships:` and **one** line under
  `Relationship properties:`. Example schema:

  ```python
  RelationshipSchema(
      label="LOCATED_IN",
      endpoints=[
          RelationshipEndpoint(source_label="City", target_label="Country"),
          RelationshipEndpoint(source_label="Landmark", target_label="Country"),
      ],
      properties=[GraphPropertySchema(name="since", dtype="INTEGER")],
  )
  ```
  Assert the formatted output contains both `(:City)-[:LOCATED_IN]->(:Country)`
  and `(:Landmark)-[:LOCATED_IN]->(:Country)`, and exactly one `LOCATED_IN {since:
  INTEGER}` line.

- If any cached schema JSON fixtures exist under `cache/` or `tests/` that embed
  the old `{"label","source_label","target_label",...}` relationship shape, they
  will fail to validate against the new model. Grep for `"source_label"` in test
  fixtures / `cache/schemas/`; regenerate or hand-migrate. Live cypherbench caches
  are rebuilt by introspection on next run.

## 8. Validation

```bash
make format
make lint          # includes import-linter (lint-arch) — no layer changes here
make mypy
make test          # or: uv run pytest tests/test_schema_browser_graph.py -q
```

Manual smoke (optional, needs a running Neo4j / cypherbench graph): connect,
call the schema formatter, confirm `The relationships:` lists every pattern and
`Relationship properties:` lists each type once.

## 9. Touch-point checklist

| File | Change |
|------|--------|
| `core/types.py:71-111` | New `RelationshipEndpoint`; `RelationshipSchema` per-type with `endpoints`; `get_relationship` + `iter_patterns` replace `get_relationships` |
| `core/__init__.py` | Re-export `RelationshipEndpoint` |
| `core/db_connector/neo4j_conn.py:18,245-308` | Key rels by type; collect endpoints; drop property fan-out; import `RelationshipEndpoint` |
| `core/formatters/cypher.py:31-80` | Iterate patterns for connectivity; drop dedup in property section; `format_relationship`→`format_pattern` |
| `app/screens.py:1360-1393` | Iterate `(type, endpoint)`; pattern count vs type count |
| `tests/test_schema_browser_graph.py` | Fixture to `endpoints=[...]`; add multi-endpoint formatter test |

## 10. Out of scope

- Collapsing the UI tree to one node per type (endpoints as a sub-group).
- Per-endpoint cardinality on `RelationshipEndpoint` (add a field only when a
  consumer needs it — do not speculatively add).
- Any non-Neo4j property-graph backend where endpoints are part of type identity.
