# Unified Data Connector and SPARQL Architecture Plan

## Goal

Add first-class support for ordinary SPARQL databases and Wikidata while moving
the connector architecture to its clean long-term shape.

The final design has:

- one structural `DataConnector` protocol;
- independent data-model, query-language, backend, and result-shape metadata;
- concrete `SQLConnector`, Neo4j/Bolt connector, and `SPARQLConnector`
  implementations;
- tagged SQL, property-graph, and RDF schema models;
- concrete optional operations outside the universal connector contract; and
- generic agent tools such as `connect_data_source`, `get_db_document`,
  `run_query`, and `write_result_table` rather than Wikidata-specific tools.

Wikidata is a configured use of the generic `SPARQLConnector`, not a separate
connector implementation.

## First-principles model

A connected source needs to support only the operations required by generic
consumers:

1. Execute a query and return a normalized result.
2. Describe its structure well enough to formulate queries.
3. Refresh that description.
4. Manage its lifecycle.

The shared boundary should therefore be approximately:

```python
class DataConnector(Protocol):
    global_id: str
    backend: str
    language: QueryLanguage
    schema: SourceSchema
    read_only: bool

    async def execute(
        self,
        query: str,
        parameters: QueryParameters = None,
        timeout: int | None = None,
    ) -> ExecResult: ...

    async def refresh_schema(self) -> SourceSchema: ...

    async def close(self) -> None: ...
```

Concrete connectors satisfy this protocol structurally and do not need a
shared base class.

The current `SQLConnectorProtocol` and `PropertyGraphConnectorProtocol` should
not be extended with a third RDF- or SPARQL-specific protocol. They should be
replaced by the single `DataConnector` boundary.

## Independent dimensions

The architecture must not infer one of these dimensions from another:

| Dimension | Examples | Consumer |
|---|---|---|
| Backend | PostgreSQL, Neo4j, Wikidata Query Service | Connection behavior and source identity |
| Query language | PostgreSQL SQL, Cypher, SPARQL | Agent query generation and syntax highlighting |
| Schema kind | Relational, property graph, RDF | Schema formatting and data explorer |
| Result shape | Table, graph, affected-row summary | Output storage and rendering |

For example:

```text
SQLConnector
  backend: postgresql
  query language: postgresql SQL
  schema kind: sql

Neo4jConnector
  backend: neo4j
  query language: cypher
  schema kind: property_graph

SPARQLConnector with Wikidata profile
  backend: wikidata-query-service
  query language: sparql
  schema kind: rdf
```

`connector_type` should ultimately disappear. Schema presentation should use
the schema discriminator, query presentation should use the query language,
and result presentation should use the result payload.

## Connector and loader boundary

A connector represents a live queryable system. A loader converts data that is
not independently queryable into a connector or workspace tables.

| Input | Mechanism |
|---|---|
| PostgreSQL, Neo4j, SPARQL endpoint, Wikidata Query Service | Data connector |
| CSV, Parquet, Hugging Face files, RDF dump | Loader |
| Result selected from a remote source for reuse | Workspace table |

Consequently, Wikidata Query Service is a `SPARQLConnector`. A future Wikidata
RDF dump workflow would be a loader feeding a local RDF database or normalized
workspace tables.

## Concrete connector shape

### SQL

Retain one `SQLConnector` because SQLAlchemy provides a genuine shared
connection and execution abstraction. Compose backend-specific strategies for
schema introspection, cancellation, read-only enforcement, and type handling
instead of introducing a connector subclass per database.

SQL-only conveniences, such as accepting SQLAlchemy `Executable` objects or
refreshing selected tables, remain concrete `SQLConnector` APIs rather than
members of the shared protocol.

### Cypher

Use a concrete connector class only where execution infrastructure is actually
shared. If the implementation is Neo4j-specific, `Neo4jConnector` is the
honest name. If several systems genuinely share Bolt execution, lifecycle, and
result behavior, a `BoltConnector` may own that shared implementation.

Do not create a universal `CypherConnector` solely because multiple products
accept Cypher. Query-language similarity alone does not imply a shared
transport implementation.

### SPARQL

Implement one `SPARQLConnector` around the standardized SPARQL HTTP protocol
and standard result formats. Support backend differences through small profiles
or composed strategies rather than subclasses.

Initial profiles:

- generic standards-compatible SPARQL endpoint; and
- Wikidata Query Service.

A profile may supply default prefixes, query guidance, supported extensions,
schema-discovery behavior, attribution, User-Agent requirements, and
conservative endpoint limits. It must not reimplement HTTP execution or result
normalization.

## Schema model

Use a tagged union of self-contained, query-ready schema documents:

```python
SourceSchema = Annotated[
    SQLSchema | PropertyGraphSchema | RDFSchema,
    Field(discriminator="kind"),
]
```

`SQLSchema` retains its SQL dialect. The schema is serialized, cached,
transformed, and formatted independently throughout the library, so moving the
dialect exclusively onto the connector would force callers to carry a
`(schema, language)` pair and permit mismatches. `SQLConnector.language` is
derived from `SQLSchema.dialect`, keeping one source of truth while still
giving generic connector consumers a uniform language property.

The nested `TableSchema` and `ColumnSchema` models may use language-neutral
names, but the root remains `SQLSchema` because it is a query-ready description
of a SQL-visible catalog, including dialect-native types and formatting
context. A language-neutral `RelationalSchema` should only be introduced when
a real non-SQL relational consumer requires one.

The RDF schema should support partial descriptions:

```python
class RDFSchema(BaseModel):
    kind: Literal["rdf"] = "rdf"
    name: str
    description: str | None = None
    namespaces: list[RDFNamespace] = []
    classes: list[RDFClassSchema] = []
    properties: list[RDFPropertySchema] = []
    complete: bool = False
```

RDF endpoints frequently lack a cheap, complete, enumerable schema. An empty
or partial class/property list is valid. Connecting must not trigger unbounded
class or property enumeration. Schema information may come from SPARQL Service
Description, SHACL, OWL/RDFS declarations, bounded introspection, or a curated
endpoint profile.

## Optional operations

Operations that are not meaningful for every connector must not be placed on
`DataConnector`. DataFrame-to-table writing remains concrete `SQLConnector`
behavior because its schema, table, and replacement semantics are SQL-specific.
`write_result_table` therefore requires a writable `SQLConnector` directly.

A capability protocol should be introduced only after another real
implementation and a generic consumer establish shared semantics. Possible
future examples include bulk RDF writing, transactions, or change streams, but
none are part of the connector contract preemptively.

## Generic query and result path

All connectors normalize execution through the same request and result path:

```text
DataConnectorRegistry
    -> DataConnector.execute(query, parameters, timeout)
    -> ExecResult
    -> OutputStore
    -> table/chart/map/graph or write_result_table
```

Expected normalization:

| Query | Result |
|---|---|
| SQL `SELECT` | DataFrame |
| SQL DML | Affected-row count |
| Cypher `RETURN` | DataFrame, optionally with property-graph payload |
| SPARQL `SELECT` | DataFrame |
| SPARQL `ASK` | One-row boolean DataFrame |
| SPARQL `CONSTRUCT`/`DESCRIBE` | RDF triples table, optionally with graph payload |

The common query request may carry positional parameters, named parameters, or
none. Each connector validates the parameter forms it supports. Generic agent
execution uses query strings; concrete SQL APIs may additionally support
SQLAlchemy objects.

## Agent interaction

The intended Wikidata workflow uses the generic tools:

```text
connect_data_source
get_db_document
run_query
write_result_table
```

`run_query` executes both entity/property lookup and data retrieval. Wikidata's
`SERVICE wikibase:mwapi` supports entity and property search within SPARQL, and
the Wikidata profile's database document should teach the agent the relevant
patterns.

Browser and shell tools remain fallbacks for documentation, diagnosis, dumps,
or unsupported bulk workflows. They should not be the primary QID/PID lookup
path because they bypass connector-level timeouts, rate limits, provenance,
structured results, and observability.

Do not initially add `query_wikidata` or `search_wikidata`. The former duplicates
`run_query`; the latter should only be considered after evaluations show that a
good source document and SPARQL search examples are insufficient. If multiple
connector families later need equivalent entity search, introduce a generic
capability and `search_entities(connector_alias, ...)` tool rather than a
Wikidata-specific tool.

## Connection syntax

An ordinary HTTPS URL is ambiguous. Use an explicit composite scheme for
SPARQL endpoints:

```text
sparql+https://query.wikidata.org/sparql
sparql+https://dbpedia.org/sparql
sparql+http://localhost:3030/dataset/query
```

Both `/connect` and `connect_data_source` should resolve this syntax through the
same data-layer constructor. The official Wikidata endpoint selects the
Wikidata profile automatically. A future public-source catalog entry named
Wikidata should resolve to the same connection specification rather than use a
separate execution path.

## Phased implementation plan

### Phase 0 — Establish the contract

- Record the architectural invariants in tests and developer documentation.
- Capture existing SQL and Neo4j behavior with focused connector-contract
  tests.
- Confirm that generic consumers need only query execution, source
  description, schema refresh, and lifecycle management.

Acceptance:

- No production behavior changes.
- The intended dependency and connector boundaries are explicit.

### Phase 1 — Replace the parallel connector protocols

- Introduce the single structural `DataConnector` protocol and
  `DataConnectorRegistry`.
- Update the registry, query tools, schema tools, app lifecycle, research
  consumers, and test doubles to depend on it.
- Make `SQLConnector` and `Neo4jConnector` satisfy the common protocol.
- Keep SQL-specific APIs on the concrete class.
- Delete `SQLConnectorProtocol`, `PropertyGraphConnectorProtocol`, and the
  protocol union without compatibility aliases.

Acceptance:

- SQL and Neo4j satisfy the same connector contract.
- Registry query execution contains no SQL-versus-graph dispatch.
- Existing SQL and Cypher behavior remains unchanged.

### Phase 2 — Separate metadata dimensions

- Add discriminators to SQL and property-graph schemas.
- Introduce `SourceSchema` and `QueryLanguage` types.
- Replace `connector_type` branches throughout data, output, agents, app, and
  research code.
- Store query language explicitly in result metadata; derive presentation from
  the result payload.
- Dispatch schema rendering from the tagged schema model.
- Keep `SQLSchema.dialect` as the source of truth and derive
  `SQLConnector.language` from it.

Acceptance:

- `connector_type` is removed.
- Renderers do not infer query language from schema kind.
- SQL and Cypher source/result rendering remains unchanged.

### Phase 3 — Keep optional operations concrete

- Keep table writing as concrete `SQLConnector` behavior until another genuine
  table-writing connector requires a shared capability.
- Rename `DataFrameWriteMode` to `TableWriteMode` because its values describe
  target-table behavior.
- Keep full schema refresh universal and SQL table-specific refresh concrete.
- Keep reusable connection release as a concrete `SQLConnector` operation for
  workflows such as dbt that must temporarily release a database file lock.
- Remove connection-release policy from generic query and schema tools.

Acceptance:

- `DataConnector` contains only universally meaningful operations.
- Non-universal operations remain on the concrete connector that implements
  their semantics.

### Phase 4 — Add RDF core and presentation

- Add `RDFSchema` and extend `SourceSchema`.
- Add SPARQL to `QueryLanguage`.
- Add RDF schema formatting and explorer presentation.
- Add SPARQL syntax highlighting in terminal and browser output.
- Test with an in-memory mock connector; do not add network behavior yet.

Acceptance:

- A mock RDF connector can be registered, documented, browsed, queried, and
  displayed without special cases in generic execution.

### Phase 5 — Implement read-only `SPARQLConnector`

- Implement standards-compatible HTTP execution with the existing async HTTP
  stack.
- Initially support `SELECT` and `ASK` with SPARQL JSON results.
- Normalize URIs, nulls, booleans, numerics, dates, language-tagged literals,
  and unfamiliar datatypes without lossy guesses.
- Add cancellation, timeout, concurrency, response-size, and row limits.
- Respect `429` and `Retry-After` and send a descriptive User-Agent.
- Attempt only lightweight service-description discovery.
- Use mocked HTTP transports for ordinary tests.

Acceptance:

- A generic SPARQL endpoint works through `run_query` and `OutputStore`.
- Fixed SPARQL results can be displayed and written to `workspace`.
- No Wikidata-specific behavior exists in generic execution or result parsing.

### Phase 6 — Add SPARQL connection resolution

- Resolve explicit `sparql+http` and `sparql+https` connection strings.
- Route `/connect` and `connect_data_source` through the same constructor.
- Support anonymous access and secure user-supplied authentication mechanisms
  without exposing arbitrary secret headers to the agent.
- Present SPARQL endpoints as RDF sources in the explorer.

Acceptance:

- User and agent connection paths produce the same `SPARQLConnector`.
- Arbitrary HTTPS resources are not guessed to be SPARQL endpoints.

### Phase 7 — Add endpoint profiles and Wikidata

- Introduce the minimal profile abstraction with generic and Wikidata profiles.
- Automatically select the Wikidata profile for the official endpoint.
- Add Wikidata prefixes, attribution, query guidance, and conservative service
  settings.
- Document labels, direct versus full statements, qualifiers, ranks,
  `wikibase:mwapi`, and geographic services.
- Keep all querying behind `run_query`.

Acceptance:

- The agent can resolve QIDs and PIDs, retrieve labels and qualifiers, run
  geographic queries, materialize results, and join them with user data using
  only the generic connector tools.

### Phase 8 — Make provenance first-class

- Store source name, source URL, query endpoint, retrieval time, and license in
  result metadata.
- Display compact provenance on result cards.
- Preserve discoverable provenance when a result is written to a workspace
  table without duplicating provenance fields into every data row.
- Keep the provenance model provider-neutral.

Acceptance:

- Wikidata and generic SPARQL results identify their origin and retrieval time.
- Materialized tables retain discoverable source metadata.

### Phase 9 — Evaluate agent reliability

- Evaluate entity ambiguity, property resolution, qualifiers, labels,
  geography, enrichment, endpoint errors, and broad-query timeouts.
- Measure valid-SPARQL rate, correct QID/PID selection, retries, timeouts,
  materialization success, and provenance preservation.
- Improve the source document, examples, and errors before adding tools.
- Add a generic entity-search capability only if evidence shows it is needed.

Acceptance:

- The generic `run_query` workflow is reliable enough for representative
  Wikidata tasks, or there is concrete evidence supporting one narrow generic
  capability.

### Phase 10 — Complete ordinary SPARQL support

- Add `CONSTRUCT` and `DESCRIBE`, initially normalized as triples tables.
- Add an RDF graph payload only when a concrete consumer needs RDF-specific
  graph semantics.
- Expand bounded schema discovery through Service Description, SHACL, and
  OWL/RDFS where available.
- Validate against representative Fuseki, Virtuoso, GraphDB, and
  Blazegraph-compatible endpoints.
- Add backend profiles only for demonstrated incompatibilities.
- Add optional SPARQL Update through an explicitly configured update endpoint,
  `read_only=False`, appropriate authentication, and update validation.
- Keep bulk RDF ingestion as an optional capability rather than part of
  `DataConnector`.

Acceptance:

- Standards-compatible SPARQL endpoints work without provider-specific code.
- Read-only mode prevents updates.
- Graph-producing queries return normalized reusable results.
- Backend profiles remain small and declarative.

## Final target

```text
DataConnector
├── SQLConnector
│   ├── SQL schema with self-contained dialect
│   ├── SQL dialect
│   └── concrete DataFrame-to-table writing
├── Neo4j/Bolt connector
│   ├── property-graph schema
│   └── Cypher
└── SPARQLConnector
    ├── RDF schema
    ├── SPARQL
    └── endpoint profile
        ├── generic
        ├── Wikidata
        └── other profiles only as justified
```

The critical sequencing rule is to complete the common connector and metadata
refactor before adding `SPARQLConnector`. SPARQL should validate the clean
abstraction rather than become a third historical branch.
