# Replace Schema Compression with Table-Family Formatting

## Goal

Keep `SQLSchema` as the authoritative physical database schema while retaining compact text rendering for warehouses with repeated partition or shard tables.

The current API creates a second, lossy `SQLSchema`:

```text
physical SQLSchema
    -> SchemaCompressor
    -> compressed SQLSchema
```

That compressed value can be passed to table lookup, schema linking, profiling, foreign-key prediction, and formatting even though several physical tables may have been replaced by one representative table. Presentation-only state (`TableNamePattern` and `SQLTableSchema.name_patterns`) has consequently leaked into core and tool lookup logic.

The replacement should compact table families only while formatting:

```text
physical SQLSchema
    -> private table-family grouping
    -> SQL schema formatter
    -> text
```

No compressed schema object should escape the formatting layer.

## Decisions

1. `SQLSchema` and `SQLTableSchema` always represent physical database objects.
2. Remove the public `SchemaCompressor` API and `output/schema_compression.py`.
3. Remove `TableNamePattern` and `SQLTableSchema.name_patterns` from core.
4. Keep partition-family grouping as private SQL-formatting behavior.
5. Group by recognized name family first, then strict structural compatibility.
6. Never mutate or return a replacement `SQLSchema`.
7. Generic formatter behavior remains faithful by default; agent configurations enable grouping explicitly.
8. Structured operations such as lookup, schema linking, profiling, and FK prediction always use the physical schema.

## Final Structure

```text
tabulaflow/output/formatting/
├── _table_families.py
├── _sql.py
├── sql_basic.py
└── sql_ddl.py
```

`_table_families.py` is private. No table-family or compressed-schema model is part of the public API.

## Private Rendering Model

Use one private immutable rendering group:

```python
@dataclass(frozen=True)
class _TableRenderGroup:
    tables: tuple[SQLTableSchema, ...]
    display_name: str
    comment: str | None = None

    @property
    def representative(self) -> SQLTableSchema:
        return self.tables[0]

    @property
    def is_family(self) -> bool:
        return len(self.tables) > 1

    @property
    def num_rows(self) -> int | None:
        if any(table.num_rows is None for table in self.tables):
            return None
        return sum(table.num_rows for table in self.tables if table.num_rows is not None)
```

This type is explicitly a rendering concern. It must not masquerade as a physical table.

## Family Detection

### Parse names first

Recognize one variable token per table name, in most-specific-first order:

```text
events_20240101 -> events_{YYYYMMDD}
events_202401   -> events_{YYYYMM}
events_2024     -> events_{YEAR}
events_001      -> events_{NUM}
```

Build patterns from the regex match span:

```python
pattern = name[: match.start()] + placeholder + name[match.end() :]
```

Do not run a second unbounded `re.sub()`, which can replace a different numeric span.

### Require strict structural compatibility

Candidate members must share:

- schema namespace;
- physical kind (`TABLE` versus `VIEW`);
- column names;
- canonical types;
- native types;
- nullability;
- primary key;
- safely compatible outgoing foreign keys.

Column order may be ignored for compatibility while the representative's order is retained for rendering.

For the initial implementation, do not group tables with incoming foreign-key references. This avoids hiding concrete FK targets without introducing relationship rewriting.

### Group by pattern and structure

The grouping key should include the detected pattern and strict signature:

```python
(
    schema_name,
    detected_pattern,
    structural_signature,
)
```

Only recognized groups with at least two members are compacted. Unmatched names and singleton groups remain individual physical tables.

This prevents unrelated structural twins from collapsing:

```text
customers(id, name)
products(id, name)
```

It also keeps separate families independent:

```text
revenue_{YYYYMMDD}
profit_{YYYYMMDD}
```

### Preserve stable order

Emit a family at the position of its first member. Preserve physical schema order for all other tables.

## Shared Formatting Preparation

Replace `select_tables_for_formatting()` with a shared preparation step:

```python
def prepare_tables_for_formatting(
    schema: SQLSchema,
    *,
    group_partitioned_tables: bool,
    max_total_columns: int | None,
) -> list[tuple[_TableRenderGroup, int]]:
    ...
```

The order of operations is:

```text
physical tables
-> optional family grouping
-> column quota per render group
-> representative column selection
```

Column quotas must be calculated after grouping so repeated partitions do not consume the entire budget.

`format_table()` always formats one physical table and does not perform grouping.

## Formatter API

Add the same option to both SQL formatters:

```python
@dataclass
class SQLDDLSchemaFormatter:
    group_partitioned_tables: bool = False
    max_total_columns: int | None = None

@dataclass
class SQLBasicSchemaFormatter:
    group_partitioned_tables: bool = False
    max_total_columns: int | None = None
```

The generic default is `False`, preserving a faithful rendering. Agent configurations that need compact prompts enable it explicitly.

## Group Metadata

For a grouped family:

- render the detected pattern as the table name;
- render a concise range or sparsity comment;
- use only structural fields proven compatible;
- sum row counts only if every member has a known count;
- omit sampled rows;
- avoid partition-specific profiling values unless they can be combined truthfully;
- render common outgoing foreign keys only when identical across every member.

Example:

```text
Table: events_{YYYYMMDD}
Partitions: YYYYMMDD from 20240101 to 20240131
Rows: 3,421,992
```

Sparse families should use bounded summaries rather than enormous value lists.

## Configuration

Replace the broad presentation setting:

```python
compress_schema: bool
```

with:

```python
group_partitioned_tables: bool
```

`BasicAgentConfig.to_formatter_kwargs()` passes the option to the selected SQL formatter:

```python
def to_formatter_kwargs(self) -> dict[str, Any]:
    return {
        "max_total_columns": self.formatter_max_total_columns,
        "group_partitioned_tables": self.group_partitioned_tables,
    }
```

## Call-Site Migration

### Structured consumers use physical schemas

Remove compression from:

- `SchemaPreprocessor`;
- `GetTableSchemaTool`;
- `GetColumnJsonSchemaTool` lookup;
- research column-description lookup;
- schema linking;
- foreign-key prediction;
- column profiling.

Remove compressed-name lookup through `name_patterns.original_names`.

If preprocessing many partition tables is too expensive, optimize the relevant operation explicitly by analyzing a representative and safely propagating results. Do not substitute a lossy schema.

### Presentation consumers configure formatters

Enable `group_partitioned_tables` when constructing formatters in:

- `DBSummarizer`;
- `RegistryGetSchemaTool`;
- `RegistryGetDBDocumentTool`;
- direct-prompting and mini agents;
- simple and ambiguous research agents;
- private ERD synthesis prompts;
- schema print/export scripts.

### Utility scripts

- `print_schema.py`: replace `--no-compress` with `--no-group-partitions`.
- `export_readable_cache.py`: group through the formatter.
- `print_dataset_stats.py`: remove `tables_compressed` or compute a presentation-only family count without exposing it as a platform API.

## Core Cleanup

Delete:

```text
TableNamePattern
SQLTableSchema.name_patterns
```

Remove `TableNamePattern` from `tabulaflow.core.__init__`.

Regenerate schema caches after this clean break.

The resulting invariant is:

> Every `SQLTableSchema` represents one real physical table or view.

## Tests

Replace compressor tests with formatter-family tests covering:

1. Dense date partitions form one family.
2. Sparse partitions produce a truthful bounded summary.
3. Unrelated structural twins remain separate.
4. Distinct revenue and profit families remain separate.
5. Tables and views never group together.
6. Native-type drift prevents grouping.
7. Nullability drift prevents grouping.
8. Foreign-key handling follows the conservative policy.
9. Aggregate row counts are correct when complete.
10. Unknown row counts suppress the aggregate.
11. Grouped families omit sampled rows.
12. Input `SQLSchema` remains unchanged.
13. Disabling grouping renders every physical table.
14. Names with multiple numeric spans replace the matched span only.
15. Month sparsity uses a month count rather than a day count.

## Implementation Sequence

1. Add `_table_families.py` and focused tests.
2. Integrate table groups into both SQL formatters.
3. Add `group_partitioned_tables` to formatter configuration.
4. Migrate prompt and document call sites.
5. Remove compression from structured consumers.
6. Remove compressed-name lookup workarounds.
7. Delete `SchemaCompressor` and its tests.
8. Remove `TableNamePattern` and `name_patterns` from core.
9. Rename configuration and CLI flags.
10. Run the complete test, lint, mypy, and architecture suites.

## Non-Goals

- No public `CompressedSQLSchema` or `TableFamily` model.
- No mutation of physical schema objects.
- No general semantic grouping of similarly shaped tables.
- No FK target rewriting in the first implementation.
- No custom public clustering-strategy API until a real consumer requires it.
