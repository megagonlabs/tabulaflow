"""Run a local output-pane preview server with representative result fixtures.

    uv run scripts/preview_output_pane.py --port 61211
    uv run scripts/preview_output_pane.py --port 61211 --full

The script reuses the production pane server, index shape, and card renderers,
but pushes synthetic turns directly. It is intended for browser inspection while
iterating on ``tabulaflow/app/pane.py`` and the HTML renderers.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import json
import math
import signal
import struct
import tempfile
import threading
import time
from base64 import b64encode
from collections.abc import Sequence
from importlib.resources import files as resource_files
from pathlib import Path

import pandas as pd

from tabulaflow.app import pane as pane_mod
from tabulaflow.app.debug import debug_chart_fixtures
from tabulaflow.app.pane import PaneCard, PaneSource, card_payload, pane_panel_for_output, render_resolved_output, turn_payload
from tabulaflow.app.pane.cards import GraphCardInput, MapCardInput, ResultCardInput, render_graph_data, render_map_data, render_result_data
from tabulaflow.app.pane import server as pane_server
from tabulaflow.app.runtime_paths import generate_session_id
from tabulaflow.chat import ChatResult
from tabulaflow.core.outputs import ChartArtifactSpec, ChoiceOption, ChoiceParameter, NumberParameter, OutputSpec, TableArtifactSpec
from tabulaflow.core.types import ExecResult, GraphView, PredQuery
from tabulaflow.toolhub import OutputResolver, OutputStore
from tabulaflow.toolhub.render_graph import materialize_graph_view, normalize_graph_spec
from tabulaflow.toolhub.render_map import normalize_map_spec

_MARKDOWN_SHOWCASE = r"""# Heading 1

## Heading 2

### Heading 3

#### Heading 4

##### Heading 5

###### Heading 6

Paragraph text is written as plain text with a blank line between paragraphs.

This is a second paragraph.

Line break using two trailing spaces at the end of a line{TWO_SPACES}
This line appears directly below the previous one.

Alternative line break using an HTML break tag:<br>
This line appears below it.

Emphasis:

*Italic text*

_Italic text_

**Bold text**

__Bold text__

***Bold and italic text***

___Bold and italic text___

~~Strikethrough text~~

Subscript using HTML: H<sub>2</sub>O

Superscript using HTML: x<sup>2</sup>

Blockquotes:

> This is a blockquote.

> This is a blockquote with multiple paragraphs.
>
> This is the second paragraph inside the blockquote.

> Nested blockquote:
>
> > This is a nested blockquote.
> >
> > > This is a deeply nested blockquote.

Unordered lists:

- Item one
- Item two
- Item three

* Item one
* Item two
* Item three

+ Item one
+ Item two
+ Item three

Nested unordered list:

- Parent item
  - Child item
    - Grandchild item

Ordered lists:

1. First item
2. Second item
3. Third item

Ordered list with repeated numbers:

1. First item
1. Second item
1. Third item

Nested ordered list:

1. Parent item
   1. Child item
      1. Grandchild item

Mixed list:

1. Ordered item
   - Unordered nested item
   - Another unordered nested item
2. Another ordered item

Task list:

- [x] Completed task
- [ ] Incomplete task
- [X] Also completed task

Links:

[Inline link](https://example.com)

[Inline link with title](https://example.com "Example title")

Reference-style link:

[Example][example-ref]

[example-ref]: https://example.com "Example title"

Collapsed reference-style link:

[Example][]

[Example]: https://example.com

Shortcut reference-style link:

[GitHub]

[GitHub]: https://github.com

Autolinks:

<https://example.com>

<name@example.com>

Images:

- `![Alt text](https://example.com/image.png)` -> ![Alt text](https://example.com/image.png)

Image with title:

- `![Alt text](https://example.com/image.png "Image title")` -> ![Alt text](https://example.com/image.png "Image title")

Image without alt text:

- `![](https://example.com/path/to/fallback-image.png)` -> ![](https://example.com/path/to/fallback-image.png)

Adjacent images:

- `![Mountain landscape](https://example.com/mountain.png) ![Forest](https://example.com/forest.png) ![City](https://example.com/city.png) ![Ocean](https://example.com/ocean.png)` -> ![Mountain landscape](https://example.com/mountain.png) ![Forest](https://example.com/forest.png) ![City](https://example.com/city.png) ![Ocean](https://example.com/ocean.png)

Images with punctuation in prose:

The selected view is ![Mountain landscape](https://example.com/mountain.png), followed by ![Forest](https://example.com/forest.png). Compare (![City](https://example.com/city.png)) and "![Ocean](https://example.com/ocean.png)" inside punctuation.

Reference-style image:

- `![Alt text][image-ref]` -> ![Alt text][image-ref]

[image-ref]: https://example.com/image.png "Image title"

Collapsed reference-style image:

- `![Collapsed image][]` -> ![Collapsed image][]

[Collapsed image]: https://example.com/collapsed-image.png "Collapsed image title"

Shortcut reference-style image:

- `![Shortcut image]` -> ![Shortcut image]

[Shortcut image]: https://example.com/shortcut-image.png "Shortcut image title"

Image used as a link:

- `[![Alt text](https://example.com/image.png)](https://example.com)` -> [![Alt text](https://example.com/image.png)](https://example.com)

Inline code:

Use `code` inside a sentence.

Code span containing backticks:

``Use `code` here``

Indented code block:

    function hello() {
      console.log("Hello");
    }

Fenced code block:

```text
Plain text code block
```

Fenced code block with language:

```python
def hello():
    print("Hello")
```

Fenced code block using tildes:

~~~javascript
console.log("Hello");
~~~

Horizontal rules:

---

***

___

Tables:

| Name | Age | City | Country | Department | Role | Employment status | Start date | Manager | Annual revenue | Quarterly target | Completion | Last active | Notes |
|:---|---:|:---:|:---|:---|:---|:---:|:---:|:---|---:|---:|---:|:---:|:---|
| Alice Martin | 30 | Paris | France | Enterprise Analytics | Senior Data Analyst | Active | 2021-03-15 | Morgan Chen | $2,450,000 | $720,000 | 94% | 2026-07-13 | Leading the international retention analysis initiative |
| Bob Tanaka | 25 | Tokyo | Japan | Customer Operations | Solutions Consultant | Active | 2023-09-04 | Priya Kapoor | $1,980,000 | $610,000 | 87% | 2026-07-14 | Coordinating the APAC enterprise migration program |
| Carmen Ruiz | 42 | Madrid | Spain | Strategic Partnerships | Regional Director | On leave | 2018-11-19 | Elena Petrova | $3,870,000 | $1,100,000 | 91% | 2026-06-28 | Expanding partner coverage across southern Europe |

Table alignment:

| Left aligned | Center aligned | Right aligned |
|:---|:---:|---:|
| Text | Text | Text |
| More | More | More |

Escaping characters:

\*This is not italic\*

\# This is not a heading

\[This is not a link\]

\`This is not code\`

Escapable characters include:

\ backslash
""".replace("{TWO_SPACES}", "  ")


def _result_input(
    *,
    result_id: str,
    label: str,
    query: str | None,
    df: pd.DataFrame | None,
    chart_spec: dict[str, object] | None = None,
    graph: GraphView | None = None,
    query_lexer: str = "sql",
) -> ResultCardInput:
    return ResultCardInput(
        label=label,
        query=query,
        df=df,
        chart_spec=chart_spec,
        graph=graph,
        query_lexer=query_lexer,
    )


def _map_card(
    *,
    map_id: str,
    label: str,
    title: str,
    layers: list[dict[str, object]],
    sources: dict[str, pd.DataFrame],
    pane_dir: Path,
) -> PaneCard:
    """Build a map card via the real spec → normalize → render pipeline."""
    normalized = normalize_map_spec({"title": title, "layers": layers}, sources)
    card = render_map_data(MapCardInput(label=label, spec=normalized, sources=sources), pane_dir)
    assert card is not None
    return card


def _graph_card(
    *,
    graph_id: str,
    label: str,
    graph_spec: dict[str, object],
    sources: dict[str, pd.DataFrame],
    pane_dir: Path,
) -> PaneCard:
    """Build a graph card via the real spec → normalize → render pipeline."""
    normalized = normalize_graph_spec(graph_spec, sources)
    graph = materialize_graph_view(normalized, sources)
    card = render_graph_data(GraphCardInput(label=label, graph=graph, layout=str(normalized.get("layout", "force"))), pane_dir)
    assert card is not None
    return card


def _render_result_inputs(result_inputs: Sequence[ResultCardInput], pane_dir: Path) -> list[PaneCard]:
    cards: list[PaneCard] = []
    for result_input in result_inputs:
        card = render_result_data(result_input, pane_dir)
        if card is not None:
            cards.append(card)
    return cards


def _push_turn(
    pane: pane_mod.OutputPane,
    pane_dir: Path,
    *,
    title: str,
    user: str,
    assistant: str,
    result_inputs: Sequence[ResultCardInput] = (),
    cards: Sequence[PaneCard] = (),
    source: PaneSource | None = None,
) -> None:
    pane.push(
        turn_payload(
            title=title,
            user=user,
            assistant=assistant,
            cards=[*cards, *_render_result_inputs(result_inputs, pane_dir)],
            source=source,
        )
    )


def _push_controls_turn(pane: pane_mod.OutputPane, pane_dir: Path) -> None:
    output_store = OutputStore()
    parameters = [
        ChoiceParameter(
            id="metric",
            label="Metric",
            choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="orders", label="Orders")],
        ),
        ChoiceParameter(
            id="period",
            label="Period",
            choices=[ChoiceOption(id="q2", label="Q2"), ChoiceOption(id="q3", label="Q3")],
        ),
        NumberParameter(
            id="min_value",
            label="Minimum value",
            min=0,
            max=140,
            step=20,
            default=60,
        ),
    ]
    source = output_store.add_parameterized_source("preview", parameters, "-- preview controls fixture")
    revenue_source = output_store.add_parameterized_source(
        "preview",
        parameters,
        "{% if metric != 'revenue' %}{{ not_applicable('Revenue detail only applies when Metric is Revenue') }}{% endif %}\n"
        "-- preview revenue-only detail fixture",
    )
    empty_source = asyncio.run(
        output_store.add_fixed_result_source(
            "preview",
            "sql",
            PredQuery(
                query="-- preview empty table fixture",
                exec_result=ExecResult(df=pd.DataFrame({"customer": pd.Series(dtype="object"), "value": pd.Series(dtype="int64")})),
            ),
        )
    )
    no_data_source = asyncio.run(
        output_store.add_fixed_result_source(
            "preview",
            "sql",
            PredQuery(query="-- preview no tabular data fixture", exec_result=ExecResult()),
        )
    )
    values = {
        ("q2", "revenue"): ("Q2", "Revenue", [120, 95, 72]),
        ("q3", "revenue"): ("Q3", "Revenue", [138, 104, 86]),
        ("q2", "orders"): ("Q2", "Orders", [42, 35, 28]),
        ("q3", "orders"): ("Q3", "Orders", [49, 39, 31]),
    }
    for metric in ("revenue", "orders"):
        for period in ("q2", "q3"):
            period_label, metric_label, metric_values = values[(period, metric)]
            full_df = pd.DataFrame(
                {
                    "customer": ["Acme", "Globex", "Initech"],
                    "period": [period_label] * 3,
                    "metric": [metric_label] * 3,
                    "value": metric_values,
                }
            )
            for min_value in range(0, 141, 20):
                df = full_df[full_df["value"] >= min_value].reset_index(drop=True)
                for min_selection in (min_value, float(min_value)):
                    selection = {"metric": metric, "period": period, "min_value": min_selection}
                    asyncio.run(
                        output_store.cache_parameterized_result(
                            source.id,
                            "sql",
                            selection,
                            PredQuery(
                                query=f"-- preview fixture for {period_label} {metric_label.lower()}, min_value={min_value}",
                                exec_result=ExecResult(df=df),
                            ),
                        )
                    )
                    if metric == "revenue":
                        detail = df.assign(note="revenue-only source")
                        asyncio.run(
                            output_store.cache_parameterized_result(
                                revenue_source.id,
                                "sql",
                                selection,
                                PredQuery(
                                    query=f"-- preview revenue-only detail fixture for {period_label}, min_value={min_value}",
                                    exec_result=ExecResult(df=detail),
                                ),
                            )
                        )
    result = ChatResult(
        text=(
            "This turn has answer-level controls. Switch the metric/period buttons or drag the minimum-value slider; "
            "the table and chart resolve through the live preview session instead of a precomputed bundle."
        ),
        output=OutputSpec(
            parameters=parameters,
            sources=[source, revenue_source, empty_source, no_data_source],
            artifacts=[
                TableArtifactSpec(id=source.id, label="top customers", source_id=source.id),
                ChartArtifactSpec(
                    id="CHART_PREVIEW_CONTROLS",
                    label="customer comparison",
                    source_id=source.id,
                    spec={
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "customer", "type": "nominal"},
                        "y": {"field": "value", "type": "quantitative"},
                        "color": {"field": "customer", "type": "nominal"},
                    },
                    "title": "Selected customer metric",
                    },
                ),
                TableArtifactSpec(id=revenue_source.id, label="revenue-only detail", source_id=revenue_source.id),
                TableArtifactSpec(id=empty_source.id, label="empty table", source_id=empty_source.id),
                TableArtifactSpec(id=no_data_source.id, label="no-data message", source_id=no_data_source.id),
            ],
        ),
    )
    cards = asyncio.run(render_resolved_output(asyncio.run(OutputResolver(output_store).resolve(result.output)), pane_dir))
    pane.push(
        turn_payload(
            title="Answer controls preview",
            user="Compare top customers, with controls for the interpretation.",
            assistant=result.text,
            cards=cards,
            panel=pane_panel_for_output(result.output),
        ),
        result=result,
        output_store=output_store,
    )


def _long_result_response(summary: str) -> str:
    return "\n\n".join(
        [
            summary,
            (
                "I kept the written response above the artifacts because it should provide context "
                "before the user starts inspecting the cited cards. The result panel below should "
                "feel attached to this explanation, but not crowded against it."
            ),
            (
                "Each card can expose multiple views. The Chart view is useful for scanning shape "
                "and trend, the Data view is useful for checking exact rows, and the Query view keeps "
                "the generated source available for audit."
            ),
            (
                "This longer preview response is meant to exercise the spacing between user bubble, "
                "assistant text, and result controls. It should remain readable as prose while leaving "
                "the first panel visible soon after the text ends."
            ),
        ]
    )


def _chart_cards(pane_dir: Path, *, limit: int | None) -> list[PaneCard]:
    cards: list[PaneCard] = []
    fixtures = debug_chart_fixtures()
    if limit is not None:
        fixtures = fixtures[:limit]
    for result_id, label, query, df, spec in fixtures:
        card = render_result_data(
            _result_input(result_id=result_id, label=label, query=query, df=df, chart_spec=spec),
            pane_dir,
        )
        if card is not None:
            cards.append(card)
    return cards


def _many_cards(cards: Sequence[PaneCard]) -> list[PaneCard]:
    if not cards:
        return []
    labels = [
        "q1",
        "top_regions",
        "sales_by_product",
        "channel_mix",
        "low_stock_alerts",
        "north_america_enterprise_revenue",
        "sku",
        "monthly_active_accounts",
        "very_long_card_label_that_should_no_longer_truncate",
        "cohort_retention",
        "x",
        "warehouse_inventory_reconciliation_status",
    ]
    return [
        card_payload(card_id=cards[i % len(cards)]["id"], label=label, views=cards[i % len(cards)]["views"])
        for i, label in enumerate(labels)
    ]


def _manual_table_card(pane_dir: Path) -> PaneCard:
    df = pd.DataFrame(
        {
            "sample_id": [f"ex-{i:04d}" for i in range(1, 13)],
            "domain": ["geography", "general", "math", "science", "history", "math"] * 2,
            "question": [
                "What is the smallest country in the world?",
                "What is the freezing point of water in Fahrenheit?",
                "What is the smallest prime number?",
                "What is the chemical symbol for gold?",
                "In what year did World War II end?",
                "How many sides does a hexagon have?",
            ]
            * 2,
            "expected_answer": ["Vatican City", "32", "2", "Au", "1945", "6"] * 2,
            "source_url": [
                "https://www.cia.gov/the-world-factbook/countries/holy-see-vatican-city/",
                "https://www.weather.gov/safety/cold-water",
                "https://oeis.org/A000040",
                "https://pubchem.ncbi.nlm.nih.gov/element/Gold",
                "https://www.nationalww2museum.org/war/articles/world-war-ii-end-dates",
                "https://mathworld.wolfram.com/Hexagon.html",
            ]
            * 2,
        }
    )
    card = render_result_data(_result_input(result_id="manual", label="", query=None, df=df), pane_dir)
    assert card is not None
    return card


def _wide_manual_table_card(pane_dir: Path) -> PaneCard:
    rows = 1_000
    cols = 60
    data: dict[str, list[object]] = {
        "row_id": list(range(1, rows + 1)),
        "segment": [f"segment_{i % 8}" for i in range(rows)],
        "status": [["ok", "review", "hold", "blocked"][i % 4] for i in range(rows)],
    }
    for col in range(1, cols - len(data) + 1):
        data[f"metric_{col:02d}"] = [round(((row * (col + 7)) % 100_000) / 37.0, 2) for row in range(rows)]
    df = pd.DataFrame(data)
    card = render_result_data(_result_input(result_id="wide_manual", label="", query=None, df=df), pane_dir)
    assert card is not None
    return card


def _push_manual_table_turn(pane: pane_mod.OutputPane, pane_dir: Path) -> None:
    pane.push(
        turn_payload(
            title="manual_table",
            source="manual",
            cards=[_manual_table_card(pane_dir)],
        )
    )
    pane.push(
        turn_payload(
            title="wide_manual_table",
            source="manual",
            cards=[_wide_manual_table_card(pane_dir)],
        )
    )


def _large_table_result(num_rows: int) -> ResultCardInput:
    df = pd.DataFrame(
        {
            "row_id": range(1, num_rows + 1),
            "region": (["north", "south", "east", "west"] * ((num_rows // 4) + 1))[:num_rows],
            "orders": [(i * 17) % 10_000 for i in range(num_rows)],
            "revenue": [round(((i * 37) % 250_000) / 3.0, 2) for i in range(num_rows)],
            "status": (["ok", "review", "hold"] * ((num_rows // 3) + 1))[:num_rows],
        }
    )
    return _result_input(
        result_id="QDEBUG_VERY_LARGE",
        label="very_large_table",
        query=f"-- synthetic {num_rows:,}-row table",
        df=df,
    )


def _large_agent_table_result() -> ResultCardInput:
    rows = 1_000
    data: dict[str, list[object]] = {
        "row_id": list(range(1, rows + 1)),
        "segment": [f"segment_{i % 8}" for i in range(rows)],
        "status": [["ok", "review", "hold", "blocked"][i % 4] for i in range(rows)],
    }
    for col in range(1, 10):
        data[f"metric_{col:02d}"] = [round(((row * (col + 5)) % 50_000) / 29.0, 2) for row in range(rows)]
    return _result_input(
        result_id="QDEBUG_LARGE_AGENT_TABLE",
        label="large_agent_table",
        query="-- synthetic 1,000-row agent result table",
        df=pd.DataFrame(data),
    )


def _cypher_graph_result() -> ResultCardInput:
    df = pd.DataFrame(
        {
            "p": [
                "(:Person {name: 'Alice'})-[:ACTED_IN {role: 'Analyst'}]->(:Movie {title: 'The Matrix'})",
                "(:Person {name: 'Bob'})-[:DIRECTED]->(:Movie {title: 'The Matrix'})",
            ]
        }
    )
    graph = GraphView(
        nodes=[
            {
                "id": "person:alice",
                "label": "Alice",
                "group": "Person",
                "properties": {"name": "Alice", "born": 1988},
            },
            {
                "id": "person:bob",
                "label": "Bob",
                "group": "Person",
                "properties": {"name": "Bob", "born": 1975},
            },
            {
                "id": "movie:matrix",
                "label": "The Matrix",
                "group": "Movie",
                "properties": {"title": "The Matrix", "released": 1999},
            },
        ],
        edges=[
            {
                "id": "rel:alice-acted-in-matrix",
                "source": "person:alice",
                "target": "movie:matrix",
                "label": "ACTED_IN",
                "directed": True,
                "properties": {"role": "Analyst"},
            },
            {
                "id": "rel:bob-directed-matrix",
                "source": "person:bob",
                "target": "movie:matrix",
                "label": "DIRECTED",
                "directed": True,
            },
        ],
    )
    return _result_input(
        result_id="QDEBUG_CYPHER_GRAPH",
        label="cypher_path_result",
        query="MATCH p=(:Person)-[r]->(:Movie) RETURN p LIMIT 2",
        df=df,
        graph=graph,
        query_lexer="cypher",
    )


def _cypher_non_graph_result() -> ResultCardInput:
    return _result_input(
        result_id="QDEBUG_CYPHER_TABLE",
        label="cypher_scalar_result",
        query=(
            "MATCH (m:Movie)<-[:ACTED_IN]-(p:Person)\n"
            "RETURN m.title AS movie, count(p) AS actor_count\n"
            "ORDER BY actor_count DESC\n"
            "LIMIT 3"
        ),
        df=pd.DataFrame(
            {
                "movie": ["The Matrix", "Inception", "Arrival"],
                "actor_count": [42, 28, 17],
            }
        ),
        query_lexer="cypher",
    )


def _map_showcase_card(pane_dir: Path) -> PaneCard:
    df = pd.DataFrame(
        [
            {
                "name": "Red pin marker",
                "kind": "points layer",
                "url": "https://www.sanjose.org/",
                "lat": 37.3336,
                "lng": -121.8906,
                "geom": None,
            },
            {
                "name": "GeoJSON point",
                "kind": "Point",
                "url": "https://geojson.org/",
                "lat": None,
                "lng": None,
                "geom": {"type": "Point", "coordinates": [-121.8815, 37.3394]},
            },
            {
                "name": "GeoJSON multipoint",
                "kind": "MultiPoint",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.3",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "MultiPoint",
                    "coordinates": [[-121.906, 37.329], [-121.900, 37.337], [-121.894, 37.331]],
                },
            },
            {
                "name": "GeoJSON line",
                "kind": "LineString",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "LineString",
                    "coordinates": [[-121.915, 37.345], [-121.904, 37.350], [-121.890, 37.346]],
                },
            },
            {
                "name": "GeoJSON multiline",
                "kind": "MultiLineString",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.5",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [[-121.925, 37.322], [-121.914, 37.327], [-121.905, 37.324]],
                        [[-121.892, 37.321], [-121.882, 37.328], [-121.873, 37.323]],
                    ],
                },
            },
            {
                "name": "GeoJSON polygon",
                "kind": "Polygon",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-121.923, 37.354],
                            [-121.908, 37.354],
                            [-121.908, 37.364],
                            [-121.923, 37.364],
                            [-121.923, 37.354],
                        ]
                    ],
                },
            },
            {
                "name": "GeoJSON multipolygon",
                "kind": "MultiPolygon",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [-121.888, 37.352],
                                [-121.879, 37.352],
                                [-121.879, 37.359],
                                [-121.888, 37.359],
                                [-121.888, 37.352],
                            ]
                        ],
                        [
                            [
                                [-121.874, 37.350],
                                [-121.866, 37.350],
                                [-121.866, 37.357],
                                [-121.874, 37.357],
                                [-121.874, 37.350],
                            ]
                        ],
                    ],
                },
            },
            {
                "name": "GeoJSON geometry collection",
                "kind": "GeometryCollection",
                "url": "https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.8",
                "lat": None,
                "lng": None,
                "geom": {
                    "type": "GeometryCollection",
                    "geometries": [
                        {"type": "Point", "coordinates": [-121.864, 37.337]},
                        {
                            "type": "LineString",
                            "coordinates": [[-121.869, 37.333], [-121.857, 37.342]],
                        },
                    ],
                },
            },
        ]
    )
    return _map_card(
        map_id="MAPDEBUG_SHOWCASE",
        label="geometry_showcase",
        title="Geometry showcase (single source)",
        sources={"QDEBUG_MAP": df},
        pane_dir=pane_dir,
        layers=[
            {
                "type": "points",
                "source_id": "QDEBUG_MAP",
                "lat": "lat",
                "lng": "lng",
                "label": "name",
                "tooltip": ["kind", "url"],
                "color": {"field": "kind"},
            },
            {
                "type": "geojson",
                "source_id": "QDEBUG_MAP",
                "geojson": "geom",
                "label": "name",
                "tooltip": ["kind", "url"],
                "color": {"field": "kind"},
            },
            {
                "type": "points",
                "points": [
                    {
                        "lat": 37.350,
                        "lng": -121.890,
                        "label": "Inline destination",
                        "kind": "inline point",
                        "url": "https://www.sanjose.org/",
                    }
                ],
                "label": "label",
                "tooltip": ["kind", "url"],
                "color": {"field": "kind"},
            },
        ],
    )


def _map_overlay_card(pane_dir: Path) -> PaneCard:
    """Multi-card overlay: neighborhood boundaries (Q1) + store points (Q2)."""
    areas = pd.DataFrame(
        [
            {
                "area": "Downtown",
                "tier": "core",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-121.895, 37.330],
                            [-121.878, 37.330],
                            [-121.878, 37.342],
                            [-121.895, 37.342],
                            [-121.895, 37.330],
                        ]
                    ],
                },
            },
            {
                "area": "North San Jose",
                "tier": "growth",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-121.945, 37.370],
                            [-121.915, 37.370],
                            [-121.915, 37.395],
                            [-121.945, 37.395],
                            [-121.945, 37.370],
                        ]
                    ],
                },
            },
        ]
    )
    stores = pd.DataFrame(
        [
            {"store": "Market St", "status": "open", "lat": 37.335, "lng": -121.888},
            {"store": "First St", "status": "open", "lat": 37.337, "lng": -121.886},
            {"store": "Almaden", "status": "closed", "lat": 37.332, "lng": -121.890},
            {"store": "Rio Robles", "status": "open", "lat": 37.382, "lng": -121.930},
            {"store": "Zanker", "status": "closed", "lat": 37.388, "lng": -121.925},
        ]
    )
    return _map_card(
        map_id="MAPDEBUG_OVERLAY",
        label="stores_by_area",
        title="Stores by service area (two query results)",
        sources={"Q_AREAS": areas, "Q_STORES": stores},
        pane_dir=pane_dir,
        layers=[
            {
                "type": "geojson",
                "source_id": "Q_AREAS",
                "geojson": "boundary",
                "label": "area",
                "tooltip": ["tier"],
                "color": {"field": "tier"},
            },
            {
                "type": "points",
                "source_id": "Q_STORES",
                "lat": "lat",
                "lng": "lng",
                "label": "store",
                "tooltip": ["status"],
                "color": {"field": "status"},
            },
        ],
    )


def _graph_network_card(pane_dir: Path) -> PaneCard:
    nodes = pd.DataFrame(
        [
            {
                "id": "alice",
                "name": "Alice Research Program Coordinator",
                "team": "Research",
                "score": 94,
                "profile": "https://example.com/people/alice",
            },
            {"id": "bob", "name": "Bob", "team": "Research", "score": 78, "profile": "https://example.com/people/bob"},
            {
                "id": "carol",
                "name": "Carol Enterprise Product Strategy Lead",
                "team": "Product",
                "score": 88,
                "profile": "https://example.com/people/carol",
            },
            {"id": "dina", "name": "Dina", "team": "Design", "score": 70, "profile": "https://example.com/people/dina"},
            {"id": "eli", "name": "Eli", "team": "Data", "score": 82, "profile": "https://example.com/people/eli"},
            {"id": "faye", "name": "Faye", "team": "Data", "score": 66, "profile": "https://example.com/people/faye"},
        ]
    )
    edges = pd.DataFrame(
        [
            {
                "src": "alice",
                "dst": "bob",
                "rel": "coauthors",
                "weight": 5,
                "doc": "https://example.com/relations/coauthors",
            },
            {
                "src": "alice",
                "dst": "carol",
                "rel": "advises",
                "weight": 3,
                "doc": "https://example.com/relations/advises",
            },
            {
                "src": "bob",
                "dst": "dina",
                "rel": "reviews",
                "weight": 2,
                "doc": "https://example.com/relations/reviews",
            },
            {
                "src": "carol",
                "dst": "eli",
                "rel": "partners",
                "weight": 4,
                "doc": "https://example.com/relations/partners",
            },
            {
                "src": "eli",
                "dst": "faye",
                "rel": "mentors",
                "weight": 2,
                "doc": "https://example.com/relations/mentors",
            },
            {"src": "faye", "dst": "alice", "rel": "syncs", "weight": 1, "doc": "https://example.com/relations/syncs"},
        ]
    )
    return _graph_card(
        graph_id="GRAPHDEBUG_NETWORK",
        label="force_layout",
        pane_dir=pane_dir,
        sources={"Q_GRAPH_NODES": nodes, "Q_GRAPH_EDGES": edges},
        graph_spec={
            "title": "Collaboration network",
            "layout": "force",
            "nodes": [
                {
                    "source_id": "Q_GRAPH_NODES",
                    "id": "id",
                    "label": "name",
                    "group": "team",
                    "tooltip": ["team", "score", "profile"],
                }
            ],
            "edges": [
                {
                    "source_id": "Q_GRAPH_EDGES",
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                    "tooltip": ["weight", "doc"],
                }
            ],
        },
    )


def _graph_properties_card(pane_dir: Path) -> PaneCard:
    long_text = (
        "This is an intentionally very long property value used to stress graph detail rendering. "
        "It should truncate inside the tooltip without breaking layout, hiding links, or pushing the "
        "popup outside the visible graph viewport. The full value remains in the graph payload and in "
        "the browser title attribute for inspection. "
        "This repeated clause makes the value exceed the graph detail truncation threshold by a wide "
        "margin so the ellipsis should be visible in the rich property graph preview."
    )
    neo4j_property_examples = {
        "string_value": "Neo4j property string",
        "long_string_value": long_text,
        "integer_value": 9_223_372_036_854_775_807,
        "negative_integer_value": -42,
        "float_value": 3.141592653589793,
        "boolean_value": True,
        "date_value": "2026-07-09",
        "local_time_value": "14:35:20.123",
        "time_value": "14:35:20.123-07:00",
        "local_datetime_value": "2026-07-09T14:35:20.123",
        "datetime_value": "2026-07-09T14:35:20.123-07:00[America/Los_Angeles]",
        "duration_value": "P1Y2M3DT4H5M6.789S",
        "point_cartesian_2d": "point({x: 12.5, y: -3.75})",
        "point_cartesian_3d": "point({x: 12.5, y: -3.75, z: 8.0})",
        "point_wgs84_2d": "point({longitude: -122.4194, latitude: 37.7749})",
        "point_wgs84_3d": "point({longitude: -122.4194, latitude: 37.7749, height: 15.2})",
        "byte_array_hex_preview": "0x6e656f346a2d6279746573",
        "string_list": ["graph", "tooltip", "property"],
        "integer_list": [1, 2, 3, 5, 8, 13],
        "float_list": [0.1, 0.25, 0.5, 0.75],
        "boolean_list": [True, False, True],
        "temporal_list": ["2026-07-09", "2026-07-10", "2026-07-11"],
        "point_list": [
            "point({longitude: -122.4194, latitude: 37.7749})",
            "point({longitude: -73.9857, latitude: 40.7484})",
        ],
        "null_renderer_stress": None,
    }
    node_stress_props = {
        f"node_property_{i:02d}": (
            f"{long_text} Field {i}." if i % 5 == 0 else {"rank": i, "flags": [f"flag_{i}", f"flag_{i + 1}"]}
        )
        for i in range(1, 31)
    }
    edge_stress_props = {
        f"relationship_property_{i:02d}": (
            [f"evidence_{i}", f"evidence_{i + 1}", f"{long_text} Edge field {i}."] if i % 6 == 0 else i / 10
        )
        for i in range(1, 31)
    }
    nodes = [
        {
            "id": "person",
            "label": "Person With Rich Properties",
            "group": "Person",
            "age": 36,
            "active": True,
            "aliases": ["Al", "A. Rivera", "Research Lead"],
            "profile": {
                "city": "Oakland",
                "skills": ["graphs", "cypher", "evaluation"],
                "links": {"homepage": "https://example.com/alice", "docs": "https://example.com/docs/alice"},
            },
            "joined": "2021-04-18",
            "notes": "Long node note intended to verify that detailed graph tooltips can carry larger property values.",
            **neo4j_property_examples,
            **node_stress_props,
        },
        {
            "id": "paper",
            "label": "Paper",
            "group": "Artifact",
            "year": 2025,
            "keywords": ["graph rendering", "tooltips", "inspection"],
            "metrics": {"citations": 42, "downloads": 1380, "featured": False},
            "url": "https://example.com/papers/graph-tooltips",
        },
        {
            "id": "team",
            "label": "Team",
            "group": "Org",
            "members": 8,
            "regions": ["US", "EU", "APAC"],
            "metadata": {"budget": "research", "priority": 2},
        },
    ]
    edges = [
        {
            "src": "person",
            "dst": "paper",
            "rel": "AUTHORED",
            "weight": 0.92,
            "roles": ["lead author", "reviewer"],
            "period": {"start": "2024-10-01", "end": "2025-02-14"},
            "evidence": "https://example.com/evidence/authored",
            **edge_stress_props,
        },
        {
            "src": "person",
            "dst": "team",
            "rel": "MEMBER_OF",
            "since": "2020-06-01",
            "allocation": {"research": 0.7, "support": 0.3},
            "flags": ["primary", "remote"],
        },
        {
            "src": "team",
            "dst": "paper",
            "rel": "SPONSORS",
            "approved": True,
            "reviewers": ["Dana", "Eli", "Morgan"],
            "metadata": {"cycle": "Q2", "risk": "low"},
        },
    ]
    return _graph_card(
        graph_id="GRAPHDEBUG_PROPERTIES",
        label="rich_properties",
        pane_dir=pane_dir,
        sources={},
        graph_spec={
            "title": "Rich property graph",
            "layout": "force",
            "nodes": [{"data": nodes, "id": "id", "label": "label", "group": "group", "tooltip": True}],
            "edges": [
                {
                    "data": edges,
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                    "tooltip": True,
                }
            ],
        },
    )


def _physics_graph_card(
    pane_dir: Path,
    *,
    shape: str,
    physics: str,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> PaneCard:
    return _graph_card(
        graph_id=f"GRAPHDEBUG_{shape.upper()}_{physics.upper()}",
        label=f"{physics}_{shape}",
        pane_dir=pane_dir,
        sources={f"Q_{shape.upper()}_NODES": nodes, f"Q_{shape.upper()}_EDGES": edges},
        graph_spec={
            "title": f"{shape.replace('_', ' ').title()} ({physics})",
            "layout": "force",
            "nodes": [
                {
                    "source_id": f"Q_{shape.upper()}_NODES",
                    "id": "id",
                    "label": "label",
                    "group": "group",
                    "tooltip": ["group"],
                }
            ],
            "edges": [
                {
                    "source_id": f"Q_{shape.upper()}_EDGES",
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                }
            ],
        },
    )


def _physics_social_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.DataFrame(
        [
            {"id": "alice", "label": "Alice", "group": "Research"},
            {"id": "bob", "label": "Bob Research Operations Liaison", "group": "Research"},
            {"id": "dina", "label": "Dina", "group": "Design"},
            {"id": "eli", "label": "Eli", "group": "Data"},
            {"id": "faye", "label": "Faye", "group": "Data"},
            {"id": "grace", "label": "Grace", "group": "Product"},
            {"id": "hugo", "label": "Hugo", "group": "Product"},
            {"id": "ivy", "label": "Ivy", "group": "Research"},
            {"id": "jules", "label": "Jules", "group": "Design"},
            {"id": "kai", "label": "Kai", "group": "Data"},
            {"id": "lena", "label": "Lena", "group": "Product"},
            {"id": "mira", "label": "Mira", "group": "Research"},
        ]
    )
    edges = pd.DataFrame(
        [
            {"src": "alice", "dst": "bob", "rel": "coauthors"},
            {"src": "alice", "dst": "dina", "rel": "advises"},
            {"src": "alice", "dst": "faye", "rel": "syncs"},
            {"src": "bob", "dst": "eli", "rel": "reviews"},
            {"src": "bob", "dst": "ivy", "rel": "pairs"},
            {"src": "dina", "dst": "jules", "rel": "designs"},
            {"src": "eli", "dst": "kai", "rel": "mentors"},
            {"src": "faye", "dst": "kai", "rel": "supports"},
            {"src": "grace", "dst": "hugo", "rel": "partners"},
            {"src": "grace", "dst": "lena", "rel": "plans"},
            {"src": "hugo", "dst": "alice", "rel": "briefs"},
            {"src": "ivy", "dst": "mira", "rel": "studies"},
            {"src": "jules", "dst": "grace", "rel": "maps"},
            {"src": "kai", "dst": "mira", "rel": "analyzes"},
            {"src": "lena", "dst": "bob", "rel": "asks"},
            {"src": "mira", "dst": "dina", "rel": "validates"},
        ]
    )
    return nodes, edges


def _physics_chain_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.DataFrame(
        {
            "id": [f"n{i}" for i in range(12)],
            "label": ["Node Six With A Very Long Process Stage Label" if i == 6 else f"N{i}" for i in range(12)],
            "group": ["Chain"] * 12,
        }
    )
    edges = pd.DataFrame(
        [{"src": f"n{i}", "dst": f"n{i + 1}", "rel": "next"} for i in range(11)]
        + [{"src": "n0", "dst": "n6", "rel": "shortcut"}, {"src": "n4", "dst": "n11", "rel": "shortcut"}]
    )
    return nodes, edges


def _physics_disconnected_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = ["Cluster A"] * 7 + ["Cluster B"] * 7
    nodes = pd.DataFrame(
        {
            "id": [f"a{i}" for i in range(7)] + [f"b{i}" for i in range(7)],
            "label": [f"A{i}" for i in range(7)] + [f"B{i}" for i in range(7)],
            "group": groups,
        }
    )
    edges = pd.DataFrame(
        [{"src": "a0", "dst": f"a{i}", "rel": "links"} for i in range(1, 7)]
        + [{"src": "b0", "dst": f"b{i}", "rel": "links"} for i in range(1, 7)]
        + [{"src": "a2", "dst": "a5", "rel": "peer"}, {"src": "b2", "dst": "b5", "rel": "peer"}]
    )
    return nodes, edges


def _physics_dense_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = pd.DataFrame(
        {
            "id": [f"d{i}" for i in range(14)],
            "label": [f"D{i}" for i in range(14)],
            "group": [f"Group {i % 3 + 1}" for i in range(14)],
        }
    )
    edges = []
    for i in range(14):
        edges.append({"src": f"d{i}", "dst": f"d{(i + 1) % 14}", "rel": "ring"})
        edges.append({"src": f"d{i}", "dst": f"d{(i + 4) % 14}", "rel": "chord"})
    return nodes, pd.DataFrame(edges)


def _physics_medium_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    count = 54
    nodes = pd.DataFrame(
        {
            "id": [f"m{i}" for i in range(count)],
            "label": [f"M{i}" for i in range(count)],
            "group": [f"Team {i % 6 + 1}" for i in range(count)],
        }
    )
    edges = []
    for i in range(count):
        edges.append({"src": f"m{i}", "dst": f"m{(i + 1) % count}", "rel": "ring"})
        if i % 2 == 0:
            edges.append({"src": f"m{i}", "dst": f"m{(i + 7) % count}", "rel": "bridge"})
        if i % 5 == 0:
            edges.append({"src": f"m{i}", "dst": f"m{(i + 17) % count}", "rel": "long_link"})
    return nodes, pd.DataFrame(edges)


def _physics_large_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    count = 180
    nodes = pd.DataFrame(
        {
            "id": [f"l{i}" for i in range(count)],
            "label": [f"L{i}" for i in range(count)],
            "group": [f"Squad {i % 9 + 1}" for i in range(count)],
        }
    )
    edges = []
    for i in range(count):
        edges.append({"src": f"l{i}", "dst": f"l{(i + 1) % count}", "rel": "ring"})
        if i % 2 == 0:
            edges.append({"src": f"l{i}", "dst": f"l{(i + 11) % count}", "rel": "bridge"})
        if i % 3 == 0:
            edges.append({"src": f"l{i}", "dst": f"l{(i + 29) % count}", "rel": "long_link"})
        if i % 9 == 0:
            edges.append({"src": f"l{i}", "dst": f"l{(i + 61) % count}", "rel": "cross_cluster"})
    return nodes, pd.DataFrame(edges)


def _physics_xlarge_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    count = 300
    nodes = pd.DataFrame(
        {
            "id": [f"x{i}" for i in range(count)],
            "label": [f"X{i}" for i in range(count)],
            "group": [f"Unit {i % 12 + 1}" for i in range(count)],
        }
    )
    edge_specs: list[tuple[int, int, str]] = []
    for i in range(count):
        edge_specs.append((i, (i + 1) % count, "ring"))
        edge_specs.append((i, (i + 13) % count, "bridge"))
    for i in range(100):
        edge_specs.append((i, (i + 97) % count, "long_link"))
    edges = pd.DataFrame({"src": f"x{src}", "dst": f"x{dst}", "rel": rel} for src, dst, rel in edge_specs)
    return nodes, edges


def _graph_live_physics_stress_cards(pane_dir: Path) -> list[PaneCard]:
    cards: list[PaneCard] = []
    for shape, data_fn in (
        ("social", _physics_social_data),
        ("chain", _physics_chain_data),
        ("disconnected", _physics_disconnected_data),
        ("dense", _physics_dense_data),
        ("medium", _physics_medium_data),
        ("large", _physics_large_data),
        ("xlarge", _physics_xlarge_data),
    ):
        nodes, edges = data_fn()
        cards.append(_physics_graph_card(pane_dir, shape=shape, physics="custom", nodes=nodes, edges=edges))
    return cards


def _graph_lineage_card(pane_dir: Path) -> PaneCard:
    nodes = pd.DataFrame(
        [
            {"id": "raw_events", "label": "Raw Events", "layer": "Raw"},
            {"id": "raw_accounts", "label": "Raw Accounts", "layer": "Raw"},
            {"id": "stg_events", "label": "Stg Events", "layer": "Stage"},
            {"id": "stg_accounts", "label": "Staging Accounts With Long Descriptive Model Name", "layer": "Stage"},
            {"id": "fct_sessions", "label": "Sessions", "layer": "Fact"},
            {"id": "dim_accounts", "label": "Accounts", "layer": "Dimension"},
            {"id": "mart_growth", "label": "Executive Growth Analytics Mart", "layer": "Mart"},
        ]
    )
    edges = pd.DataFrame(
        [
            {"from_id": "raw_events", "to_id": "stg_events", "rel": "feeds"},
            {"from_id": "raw_accounts", "to_id": "stg_accounts", "rel": "feeds"},
            {"from_id": "stg_events", "to_id": "fct_sessions", "rel": "builds"},
            {"from_id": "stg_accounts", "to_id": "dim_accounts", "rel": "builds"},
            {"from_id": "fct_sessions", "to_id": "mart_growth", "rel": "aggregates"},
            {"from_id": "dim_accounts", "to_id": "mart_growth", "rel": "joins"},
        ]
    )
    return _graph_card(
        graph_id="GRAPHDEBUG_LINEAGE",
        label="layered_layout",
        pane_dir=pane_dir,
        sources={"Q_LINEAGE_NODES": nodes, "Q_LINEAGE": edges},
        graph_spec={
            "title": "dbt lineage DAG",
            "layout": "layered",
            "nodes": [
                {
                    "source_id": "Q_LINEAGE_NODES",
                    "id": "id",
                    "label": "label",
                    "group": "layer",
                    "tooltip": ["layer"],
                }
            ],
            "edges": [
                {
                    "source_id": "Q_LINEAGE",
                    "source": "from_id",
                    "target": "to_id",
                    "label": "rel",
                }
            ],
        },
    )


def _graph_tree_card(pane_dir: Path) -> PaneCard:
    nodes = pd.DataFrame(
        [
            {"id": "hq", "label": "HQ", "group": "Org"},
            {"id": "sales", "label": "Sales", "group": "Dept"},
            {"id": "product", "label": "Product Experience And Platform Department", "group": "Dept"},
            {"id": "data", "label": "Data", "group": "Dept"},
            {"id": "east", "label": "East", "group": "Team"},
            {"id": "west", "label": "West", "group": "Team"},
            {"id": "growth", "label": "Growth", "group": "Team"},
            {"id": "platform", "label": "Platform Reliability Enablement Team", "group": "Team"},
            {"id": "analytics", "label": "Analytics", "group": "Team"},
        ]
    )
    edges = pd.DataFrame(
        [
            {"src": "hq", "dst": "sales", "rel": "owns"},
            {"src": "hq", "dst": "product", "rel": "owns"},
            {"src": "hq", "dst": "data", "rel": "owns"},
            {"src": "sales", "dst": "east", "rel": "leads"},
            {"src": "sales", "dst": "west", "rel": "leads"},
            {"src": "product", "dst": "growth", "rel": "leads"},
            {"src": "product", "dst": "platform", "rel": "leads"},
            {"src": "data", "dst": "analytics", "rel": "leads"},
        ]
    )
    return _graph_card(
        graph_id="GRAPHDEBUG_TREE",
        label="tree_layout",
        pane_dir=pane_dir,
        sources={"Q_TREE_NODES": nodes, "Q_TREE_EDGES": edges},
        graph_spec={
            "title": "Org tree",
            "layout": "tree",
            "nodes": [
                {
                    "source_id": "Q_TREE_NODES",
                    "id": "id",
                    "label": "label",
                    "group": "group",
                    "tooltip": ["group"],
                }
            ],
            "edges": [
                {
                    "source_id": "Q_TREE_EDGES",
                    "source": "src",
                    "target": "dst",
                    "label": "rel",
                }
            ],
        },
    )


def _wav_bytes(freq_hz: float, seconds: float = 0.4, rate: int = 8000) -> bytes:
    n_samples = int(seconds * rate)
    samples = bytearray()
    amp = 12_000
    for i in range(n_samples):
        samples += struct.pack("<h", int(amp * math.sin(2 * math.pi * freq_hz * i / rate)))
    data_size = len(samples)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", data_size)
    return bytes(header + samples)


def _media_table_result() -> ResultCardInput:
    names = ["red", "green", "blue", "amber", "violet"]
    assets = resource_files("tabulaflow.app.assets.debug")
    jpeg = [assets.joinpath(f"jpeg_{i}.jpg").read_bytes() for i in range(5)]
    gif = [assets.joinpath(f"gif_{i}.gif").read_bytes() for i in range(5)]
    pdf = [assets.joinpath(f"pdf_{i}.pdf").read_bytes() for i in range(5)]
    wav = [_wav_bytes(f) for f in (262.0, 294.0, 330.0, 349.0, 392.0)]
    mp4_bytes = assets.joinpath("sample.mp4").read_bytes()
    jpeg_b64 = [b64encode(blob).decode("ascii") for blob in jpeg]
    df = pd.DataFrame(
        {
            "name": names,
            "jpeg": jpeg,
            "gif": gif,
            "pdf": pdf,
            "wav": wav,
            "mp4": [mp4_bytes for _ in names],
            "jpeg_b64": jpeg_b64,
            "jpeg_data_uri": [f"data:image/jpeg;base64,{payload}" for payload in jpeg_b64],
            "mixed": [jpeg[0], "plain text", 42, None, "another"],
        }
    )
    return _result_input(
        result_id="QDEBUG_MEDIA",
        label="debug_media",
        query="-- synthetic media payloads (JPEG/GIF/PDF/WAV/MP4)",
        df=df,
    )


def _serve_fixed_port(host: str, port: int, pane_dir: Path) -> pane_mod.OutputPane:
    pane = pane_mod.OutputPane(pane_dir, host=host, port=port, session_id=generate_session_id())
    handler = functools.partial(_PreviewHandler, directory=str(pane_dir))
    server = pane_server._PaneServer((host, port), handler, pane)  # noqa: SLF001
    pane._server = server  # noqa: SLF001
    pane._port = port  # noqa: SLF001
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return pane


class _PreviewHandler(pane_server._Handler):  # noqa: SLF001
    """Serve the local preview at the origin root instead of a token path."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API name)
        if self.path.startswith("/assets/"):
            super().do_GET()
            return
        clean = self.path.split("?", 1)[0]
        session_path = clean.lstrip("/")
        if session_path in ("", "index.html"):
            self._send_pane_html()
            return
        if session_path == "events":
            self._serve_events()
            return
        if session_path.endswith(".data.json") or "/" in session_path:
            self._serve_pane_file(self.path.lstrip("/"))
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802 (http.server API name)
        if self.path.split("?", 1)[0].lstrip("/") != "resolve":
            self.send_error(404)
            return
        assert isinstance(self.server, pane_server._PaneServer)  # noqa: SLF001
        pane = self.server.pane
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            request = json.loads(body)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400)
            return
        if not isinstance(request, dict):
            self.send_error(400)
            return
        turn_id = request.get("turn_id")
        selection = request.get("selection")
        if not isinstance(turn_id, int) or not isinstance(selection, dict):
            self.send_error(400)
            return
        try:
            cards = asyncio.run(pane.resolve_turn(turn_id, selection))
        except KeyError:
            self._send_json({"error": "turn is not available for live resolution"}, status=404)
            return
        self._send_json({"selection": selection, "cards": cards})


def _preview_url(host: str, port: int) -> str:
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::", "localhost") else host
    if ":" in display_host and not display_host.startswith("["):
        display_host = f"[{display_host}]"
    return f"http://{display_host}:{port}/"


def _populate_pane(
    pane: pane_mod.OutputPane,
    pane_dir: Path,
    *,
    large_rows: int,
    include_large: bool,
    include_media: bool,
    all_chart_turns: bool,
) -> None:
    chart_cards = _chart_cards(pane_dir, limit=None if all_chart_turns else 6)

    pane.push(
        turn_payload(
            title="long text-only answer",
            user="Explain the output pane experience in detail.",
            assistant="\n\n".join(
                [
                    (
                        "The output pane mirrors the agent's useful artifacts in a browser surface. "
                        "It is intentionally separate from the terminal so large tables, charts, query "
                        "text, and longer written answers can breathe without crowding the TUI."
                    ),
                    (
                        "A text-only turn should still feel complete. The user message anchors the "
                        "request, and the assistant response takes the full content width so it reads "
                        "like a document rather than a chat bubble."
                    ),
                    (
                        "Markdown prose can include rendered math, such as inline \\(R^2 = 1 - "
                        "\\frac{\\sum_i (y_i - \\hat{y}_i)^2}{\\sum_i (y_i - \\bar{y})^2}\\), "
                        "without changing the surrounding paragraph rhythm."
                    ),
                    (
                        "A display equation should stay inside the reading column and scroll horizontally "
                        "if needed:\n\n\\[\n"
                        "\\operatorname{softmax}(z_i) = \\frac{e^{z_i}}{\\sum_{j=1}^{K} e^{z_j}}\n"
                        "\\]"
                    ),
                    (
                        "When cited cards are present, each result gets the same inspection model: "
                        "card selection first, then the Chart, Data, and Query views. This keeps the "
                        "mental model predictable even when one turn contains many cards."
                    ),
                    (
                        "The browser pane should also handle idle and transitional states cleanly. "
                        "Before the first output arrives, it shows a quiet empty state. After output "
                        "arrives, the turn rail becomes a stable navigation surface rather than a log "
                        "that constantly reshapes the current view."
                    ),
                    (
                        "Long text needs extra scroll breathing room at the bottom. Without that padding, "
                        "the last paragraph lands against the viewport edge, which makes reading and "
                        "selection feel cramped."
                    ),
                    (
                        "This fixture is deliberately verbose so the preview has enough vertical content "
                        "to test scrolling, bottom padding, and transcript spacing without relying on a "
                        "table or chart view."
                    ),
                    (
                        "The desired behavior is simple: the final paragraph should be scrollable past "
                        "the bottom edge a bit, the sidebar should stay fixed, and the message rhythm "
                        "should remain calm even when the response is long."
                    ),
                ]
                * 3
            ),
            cards=[],
        )
    )

    if chart_cards:
        _push_manual_table_turn(pane, pane_dir)
        _push_controls_turn(pane, pane_dir)
        _push_turn(
            pane,
            pane_dir,
            title="Large agent table",
            user="Show a large table as a normal agent result.",
            assistant=(
                "This is a normal agent result card with 1,000 rows, so the Data view should use "
                "the compact output-pane table frame and internal scrolling."
            ),
            result_inputs=[_large_agent_table_result()],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Cypher graph auto-view",
            user="Show two Cypher query results: one with an extracted graph view and one scalar table result.",
            assistant=(
                "The first Cypher result simulates a native path query, so the card opens with Graph, Data, "
                "and Query views. The second Cypher result is scalar-only, so it should only show Data and Query."
            ),
            result_inputs=[_cypher_graph_result(), _cypher_non_graph_result()],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Single chart result",
            user="Show one chart result with its supporting data and query.",
            assistant=_long_result_response(
                "I generated one chart result. Use the Chart, Data, and Query tabs to inspect the "
                "visualization, the backing rows, and the generated SQL."
            ),
            cards=chart_cards[:1],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Map result",
            user="Show locations on an interactive map.",
            assistant="A standalone map card showing every supported geometry type from one query result.",
            cards=[_map_showcase_card(pane_dir)],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Multi-card map overlay",
            user="Overlay store locations on neighborhood service areas.",
            assistant=(
                "This map overlays two separate query results: neighborhood boundaries from one query and "
                "store points from another. Each layer reads from its own source dataset."
            ),
            cards=[_map_overlay_card(pane_dir)],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Graph layout comparison",
            user="Show one live-physics graph for each graph layout mode.",
            assistant=(
                "This turn contains one live-physics graph card for each supported layout mode: force, tree, and "
                "layered. Use the card tabs to switch layouts while inspecting the same graph renderer styling."
            ),
            cards=[
                _graph_network_card(pane_dir),
                _graph_tree_card(pane_dir),
                _graph_lineage_card(pane_dir),
                _graph_properties_card(pane_dir),
            ],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Mixed artifact counts",
            user="Show a turn containing every artifact type with mixed single and repeated counts.",
            assistant=(
                "This preview turn combines two map cards, one graph card, two chart cards, and one table card "
                "so the sidebar can show both icon-only single artifacts and icon-plus-count repeated artifacts."
            ),
            cards=[
                _map_showcase_card(pane_dir),
                _map_overlay_card(pane_dir),
                _graph_network_card(pane_dir),
                *chart_cards[:2],
            ],
            result_inputs=[_large_agent_table_result()],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Graph live physics stress test",
            user="Show custom live physics on varied graph shapes.",
            assistant=(
                "This preview-only turn exercises the custom live-physics behavior on social, chain, "
                "disconnected, dense, medium, large, and 300-node / 700-edge extra-large graph fixtures."
            ),
            cards=_graph_live_physics_stress_cards(pane_dir),
        )
        _push_turn(
            pane,
            pane_dir,
            title="Compare the first four chart fixtures",
            user="Compare the first four chart fixtures and call out the useful result views.",
            assistant=_long_result_response(
                "I generated four cited result cards. Use the card tabs to switch between fixtures, "
                "then the Chart, Data, and Query tabs to inspect each card."
            ),
            cards=chart_cards[:4],
        )
        _push_turn(
            pane,
            pane_dir,
            title="Many-card wrapping test",
            user="Show a single turn with many cards and varied label lengths.",
            assistant=_long_result_response(
                "This turn intentionally mixes short, medium, and long card labels to exercise "
                "wrapping and active-tab sizing without label truncation."
            ),
            cards=_many_cards(chart_cards),
        )

    if include_large:
        _push_turn(
            pane,
            pane_dir,
            title="Very large table",
            user="Render a very large table so I can inspect truncation and internal scrolling.",
            assistant=(
                f"This table has {large_rows:,} source rows. The browser table renderer may cap "
                "the rendered rows and report that in the Data view caption."
            ),
            result_inputs=[_large_table_result(large_rows)],
        )

    if include_media:
        _push_turn(
            pane,
            pane_dir,
            title="Multimedia table",
            user="Render the debug multimedia table.",
            assistant=(
                "This table exercises image, GIF, PDF, audio, video, base64 image, data URI, and mixed-content cells."
            ),
            result_inputs=[_media_table_result()],
        )

    if all_chart_turns:
        for i, card in enumerate(chart_cards[4:], start=5):
            pane.push(
                turn_payload(
                    title=card["label"] or f"query {i}",
                    user=f"Show fixture {i}.",
                    assistant="Here is the rendered chart, source data, and query for this fixture.",
                    cards=[card],
                )
            )

    if chart_cards:
        pane.push(
            turn_payload(
                title="Markdown syntax showcase",
                user="Show the Markdown rendering fixture with representative result artifacts.",
                assistant=_MARKDOWN_SHOWCASE,
                cards=chart_cards[:2],
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61211)
    parser.add_argument("--large-rows", type=int, default=60_000)
    parser.add_argument("--full", action="store_true", help="Include all chart turns and expensive stress fixtures.")
    parser.add_argument("--all-chart-turns", action="store_true", help="Render every chart fixture as its own turn.")
    parser.add_argument("--large-table", action="store_true", help="Include the very large table stress fixture.")
    parser.add_argument("--media", action="store_true", help="Include the multimedia table stress fixture.")
    parser.add_argument("--no-large-table", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-media", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    pane_dir = Path(tempfile.mkdtemp(prefix="tabulaflow-pane-preview-"))
    pane = _serve_fixed_port(args.host, args.port, pane_dir)
    _populate_pane(
        pane,
        pane_dir,
        large_rows=args.large_rows,
        include_large=(args.full or args.large_table) and not args.no_large_table,
        include_media=(args.full or args.media) and not args.no_media,
        all_chart_turns=args.full or args.all_chart_turns,
    )

    print(f"READY {_preview_url(args.host, args.port)}", flush=True)
    print(f"pane: {pane_dir}", flush=True)
    print("Press Ctrl-C to stop.", flush=True)

    stop = threading.Event()

    def _stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    try:
        while not stop.is_set():
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        pane.stop()


if __name__ == "__main__":
    main()
