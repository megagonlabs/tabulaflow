# Interpretation Panel Design Notes

Status: implemented through output parameter controls in the TUI and browser pane.

## Goal

Add a research-preview feature that lets the agent expose consequential query ambiguities as a compact interpretation panel. The user can choose among interpretation options, and the result artifacts update dynamically.

The desired user mental model is:

> I choose what I meant; the result cards update together.

## Product direction

- The panel is a turn-level controller over a result artifact bundle.
- Interpretation choices should not be mixed into the artifact card bar.
- Artifact cards remain outputs: tables, charts, maps, graphs, queries, etc.
- The same interpretation state applies to all artifacts in the bundle.
- When the user changes interpretation, the UI should preserve the currently selected artifact by stable role when possible.
- Comparison across interpretations should be a separate explicit mode later, not the default interaction.

## Current UI

Current interaction model:

- `↑↓`: move interpretation cursor
- `Enter`: apply highlighted interpretation
- `←/→`: switch artifact
- `[` / `]`: switch artifact view (`Data` / `Query`)

The interpretation area uses a config-panel-like model:

- `❯` marks the cursor row.
- `●` marks the currently applied choice.
- Results update only after `Enter`.

Current visual direction:

```text
Refine interpretation                         ↑↓ Move · ↵ Apply

Ranking
  ❯ ● Highest net revenue
      Most orders
      Highest gross revenue

Time period
    ● Last completed calendar quarter
      Current quarter to date
      Last 90 days

────────────────────────────────────────

 Top customers  Region summary  Segment breakdown       [/] Data

<artifact preview>
```

Notes:

- The title is `Refine interpretation`, styled `bold dim`.
- Ambiguity point labels are short phrases, not full questions.
- Mention spans such as `"last quarter"` are hidden by default.
- Choices are one-column, without descriptions by default.
- Artifact/view hints live near the controls they affect.
- There is no visible `q Quit` hint in the panel.

## Artifact model

Each interpretation selection maps to an artifact bundle. Each artifact should have a stable role:

```text
selection = {ranking: net_revenue, period: last_90_days}
  top_customers     -> Q12
  region_summary    -> Q13
  segment_breakdown -> Q14
```

Artifact roles are used to preserve user context when switching interpretations. For example, if the user is viewing `region_summary` and changes the interpretation, the UI should keep showing `region_summary` if that role exists for the new selection.

The design should be artifact-kind agnostic. A bundle may contain records, charts, maps, or graphs. The panel should not need special map/graph-specific ambiguity behavior.

## Agent-facing design direction

We want a clean interface with separated responsibilities:

1. Interpretation-space declaration defines user-facing ambiguity structure.
2. Query execution computes artifacts and binds them to interpretation selections.
3. Panel creation validates coverage and renders/returns the interactive panel artifact.

### Interpretation space should be semantic only

The interpretation-space tool should not contain SQL fragments or query logic.

Good:

```json
{
  "ambiguity_points": [
    {
      "id": "ranking",
      "label": "Ranking",
      "choices": [
        {"id": "net_revenue", "label": "Highest net revenue"},
        {"id": "order_count", "label": "Most orders"},
        {"id": "gross_revenue", "label": "Highest gross revenue"}
      ]
    },
    {
      "id": "period",
      "label": "Time period",
      "choices": [
        {"id": "completed_quarter", "label": "Last completed calendar quarter"},
        {"id": "last_90_days", "label": "Last 90 days"}
      ]
    }
  ],
  "default_selection": {
    "ranking": "net_revenue",
    "period": "completed_quarter"
  }
}
```

Avoid putting SQL logic into choices, such as `metric_expr`, `period_filter`, etc. Those belong to query execution.

### Query alignment idea

The preferred direction is to let Jinja query templates receive the current selection IDs, while keeping the interpretation structure separate.

For each expanded selection, the Jinja context would contain values such as:

```python
ranking = "net_revenue"
period = "last_90_days"
selection = {"ranking": "net_revenue", "period": "last_90_days"}
```

Then the SQL owns the SQL logic:

```sql
SELECT
  customer_name AS customer,
  {% if ranking == "net_revenue" %}
  SUM(net_revenue_usd) AS net_revenue_usd
  {% elif ranking == "gross_revenue" %}
  SUM(gross_revenue_usd) AS gross_revenue_usd
  {% elif ranking == "order_count" %}
  COUNT(*) AS orders
  {% endif %}
FROM orders
WHERE status = 'completed'
  AND (
    {% if period == "completed_quarter" %}
    order_date >= DATE '2026-04-01' AND order_date < DATE '2026-07-01'
    {% elif period == "last_90_days" %}
    order_date > DATE '2026-07-29' - INTERVAL 90 DAY
    {% endif %}
  )
GROUP BY customer_name
ORDER BY 2 DESC
LIMIT 5
```

This keeps the boundary cleaner than storing SQL fragments in the interpretation-space declaration.

## Proposed tool surface

### 1. Create interpretation space

Possible tool:

```python
create_interpretation_space(
    ambiguity_points: list[AmbiguityPoint],
    default_selection: dict[str, str],
) -> InterpretationSpace
```

Where:

```python
AmbiguityPoint:
    id: str
    label: str
    choices: list[InterpretationChoice]

InterpretationChoice:
    id: str
    label: str
```

Optional future fields:

- `mention`: hidden/debug source phrase, not shown by default.
- `description`: optional, hidden by compact default UI.

### 2. Enhanced query execution

We likely do not need a heavy `mode` parameter in v1. But query expansion should not be fully implicit. The query call still needs explicit binding to an interpretation space and artifact role.

Possible minimal enhancement:

```python
run_query(
    db_alias: str,
    query: str,
    refresh: bool = False,
    interpretation_space: str | None = None,
    artifact_role: str | None = None,
    artifact_label: str | None = None,
    selections: list[dict[str, str]] | None = None,
)
```

Semantics:

- If `interpretation_space` is absent, `run_query` behaves exactly as it does today.
- If `interpretation_space` is present:
  - `query` is treated as a Jinja template.
  - The tool renders and runs the query for interpretation selections.
  - If `selections` is omitted, expand over the full cartesian product.
  - If `selections` is provided, run only those exact selections.
  - Each result is registered under `(space_id, selection, artifact_role)`.
  - `artifact_role` is required.

This gives the agent a clean way to precompute all combinations, while still allowing multiple `run_query` calls when SQL varies significantly across interpretations.

### 3. Create/finalize interpretation panel

Possible tool:

```python
create_interpretation_panel(
    space_id: str,
    artifact_roles: list[ArtifactRole],
) -> InterpretationPanelArtifact
```

Where:

```python
ArtifactRole:
    role: str
    label: str
    primary: bool = False
```

The panel tool should discover previously registered interpretation-bound query results and validate coverage.

Recommended v1 behavior: fail unless every interpretation selection has every required artifact role.

## Why not fully implicit query expansion?

A fully implicit design like this is not recommended:

```python
create_interpretation_space(...)
run_query(query="...")  # magically expands if template references ranking/period
```

Reasons:

- It changes normal `run_query` semantics in surprising ways.
- The tool still needs `artifact_role` for panel assembly.
- Multiple interpretation spaces would be ambiguous.
- Hidden expansion can create many query records unexpectedly.
- Coverage validation needs explicit `(space_id, selection, role)` bindings.

Therefore, the query call should explicitly opt into interpretation expansion, but the interface should remain lightweight.

## Open questions

- Should interpretation-aware execution be an enhancement to `run_query` or a sibling tool such as `run_interpretation_query`?
- Should `selections` support patterns/wildcards, or only exact selections in v1?
- Should there be a cap on cartesian expansion size, e.g. 24 or 36 variants?
- How should non-query artifacts such as charts/maps/graphs bind to interpretation selections?
- Should the panel itself be a new citable artifact kind, e.g. `PANEL1`, or be embedded directly in `ChatResult`?
- Should the browser output pane support the same interaction model immediately, or should v1 be TUI-only?
