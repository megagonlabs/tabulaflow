"""Run a local output-pane preview server with representative result fixtures.

    uv run scripts/app/preview_output_pane.py --port 61211
    uv run scripts/app/preview_output_pane.py --port 61211 --full

The script reuses the production pane server, index shape, and card renderers,
but pushes synthetic turns directly. It is intended for browser inspection while
iterating on ``tabulaflow/app/pane.py`` and the HTML renderers.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import json
import signal
import tempfile
import threading
import time
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from _output_pane_fixtures import (
    _cypher_graph_result,
    _cypher_non_graph_result,
    _graph_lineage_card,
    _graph_live_physics_stress_cards,
    _graph_network_card,
    _graph_properties_card,
    _graph_tree_card,
    _map_overlay_card,
    _map_showcase_card,
    _media_table_result,
    _render_result_inputs,
    _result_input,
)
from _preview_fixtures import debug_chart_fixtures
from tabulaflow.agents.chat import ChatResult
from tabulaflow.app import pane as pane_mod
from tabulaflow.app.pane.contract import (
    PaneCard,
    PaneSource,
    card_payload,
    pane_panel_for_output,
    turn_payload,
)
from tabulaflow.app.pane.cards import ResultCardInput, render_resolved_output, render_result_data
import tabulaflow.app.pane.server as pane_server
from tabulaflow.app.runtime_paths import generate_session_id
from tabulaflow.app.turn import TurnOutput
from tabulaflow.output.specs import (
    ChartArtifactSpec,
    ChoiceOption,
    ChoiceParameter,
    GraphArtifactSpec,
    MapArtifactSpec,
    NumberParameter,
    OutputSpec,
    ParameterSpec,
    TableArtifactSpec,
)
from tabulaflow.core import ExecResult
from tabulaflow.output.store import OutputStore

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
    customer_parameters: list[ParameterSpec] = [
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
    zone_area_parameter = NumberParameter(
        id="min_zone_area_km2",
        label="Approx. minimum taxi-zone area",
        min=0,
        max=40,
        step=5,
        default=5,
        unit="km²",
    )
    parameters = [*customer_parameters, zone_area_parameter]
    source = output_store.add_parameterized_artifact_source(
        "preview", customer_parameters, "-- preview controls fixture"
    )
    revenue_source = output_store.add_parameterized_artifact_source(
        "preview",
        customer_parameters,
        "{% if metric != 'revenue' %}{{ not_applicable('Revenue detail only applies when Metric is Revenue') }}{% endif %}\n"
        "-- preview revenue-only detail fixture",
    )
    empty_source = asyncio.run(
        output_store.add_fixed_artifact_source(
            "preview",
            "duckdb",
            "-- preview empty table fixture",
            ExecResult(df=pd.DataFrame({"customer": pd.Series(dtype="object"), "value": pd.Series(dtype="int64")})),
        )
    )
    no_data_source = asyncio.run(
        output_store.add_fixed_artifact_source(
            "preview",
            "duckdb",
            "-- preview no tabular data fixture",
            ExecResult(),
        )
    )
    taxi_zone_source = output_store.add_parameterized_artifact_source(
        "preview",
        [zone_area_parameter],
        "-- preview NYC taxi zones filtered by minimum area",
    )
    taxi_zone_rows = json.loads(
        (Path(__file__).resolve().parents[2] / "tabulaflow/app/assets/samples/nyc_taxi_zones.json").read_text(
            encoding="utf-8"
        )
    )
    taxi_zones = pd.DataFrame(
        {
            "zone": [row["zone"] for row in taxi_zone_rows],
            "borough": [row["borough"] for row in taxi_zone_rows],
            "approx_area_km2": [round(float(row["shape_area"]) * 9_400, 2) for row in taxi_zone_rows],
            "location_id": [int(row["locationid"]) for row in taxi_zone_rows],
            "geojson": [json.dumps(row["the_geom"], separators=(",", ":")) for row in taxi_zone_rows],
        }
    )
    for min_area in range(0, 41, 5):
        filtered_zones = taxi_zones[taxi_zones["approx_area_km2"] >= min_area].reset_index(drop=True)
        for min_selection in (min_area, float(min_area)):
            asyncio.run(
                output_store.cache_parameterized_result(
                    taxi_zone_source.id,
                    "duckdb",
                    {"min_zone_area_km2": min_selection},
                    f"-- preview NYC taxi zones with approx_area_km2 >= {min_area}",
                    ExecResult(df=filtered_zones),
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
                    "latitude": [37.7749, 40.7128, 47.6062],
                    "longitude": [-122.4194, -74.0060, -122.3321],
                }
            )
            for min_value in range(0, 141, 20):
                df = full_df[full_df["value"] >= min_value].reset_index(drop=True)
                for min_selection in (min_value, float(min_value)):
                    selection = {"metric": metric, "period": period, "min_value": min_selection}
                    asyncio.run(
                        output_store.cache_parameterized_result(
                            source.id,
                            "duckdb",
                            selection,
                            f"-- preview fixture for {period_label} {metric_label.lower()}, min_value={min_value}",
                            ExecResult(df=df),
                        )
                    )
                    if metric == "revenue":
                        detail = df.assign(note="revenue-only source")
                        asyncio.run(
                            output_store.cache_parameterized_result(
                                revenue_source.id,
                                "duckdb",
                                selection,
                                f"-- preview revenue-only detail fixture for {period_label}, min_value={min_value}",
                                ExecResult(df=detail),
                            )
                        )
    result = ChatResult(
        text=(
            "This turn has answer-level controls. Switch the metric/period buttons or drag either slider; the customer "
            "artifacts and NYC taxi-zone map resolve independently through the live preview session."
        ),
        output=OutputSpec(
            parameters=parameters,
            sources=[source, revenue_source, taxi_zone_source, empty_source, no_data_source],
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
                            "color": {
                                "field": "customer",
                                "type": "nominal",
                                "scale": {"domain": ["Acme", "Globex", "Initech"]},
                            },
                        },
                        "title": "Selected customer metric",
                    },
                ),
                MapArtifactSpec(
                    id="MAP_PREVIEW_CONTROLS",
                    label="customer locations",
                    source_ids=[source.id],
                    spec={
                        "title": "Selected customer locations",
                        "layers": [
                            {
                                "type": "points",
                                "source_id": source.id,
                                "lat": "latitude",
                                "lng": "longitude",
                                "label": "customer",
                                "tooltip": ["period", "metric", "value"],
                                "color": {"field": "metric", "domain": ["Revenue", "Orders"]},
                                "size": {"field": "value", "domain": [0, 140]},
                            }
                        ],
                    },
                ),
                GraphArtifactSpec(
                    id="GRAPH_PREVIEW_CONTROLS",
                    label="customer metric network",
                    source_ids=[source.id],
                    spec={
                        "title": "Selected customer metric network",
                        "group_domain": ["Customer", "Metric"],
                        "nodes": [
                            {
                                "source_id": source.id,
                                "id": "customer",
                                "label": "customer",
                                "group": {"value": "Customer"},
                                "tooltip": ["period", "value"],
                            },
                            {
                                "source_id": source.id,
                                "id": "metric",
                                "label": "metric",
                                "group": {"value": "Metric"},
                            },
                        ],
                        "edges": [
                            {
                                "source_id": source.id,
                                "source": "customer",
                                "target": "metric",
                                "label": "period",
                                "tooltip": "value",
                            }
                        ],
                    },
                ),
                MapArtifactSpec(
                    id="MAP_PREVIEW_TAXI_ZONES",
                    label="NYC taxi zones",
                    source_ids=[taxi_zone_source.id],
                    spec={
                        "title": "NYC taxi zones by area",
                        "layers": [
                            {
                                "type": "geojson",
                                "source_id": taxi_zone_source.id,
                                "geojson": "geojson",
                                "label": "zone",
                                "tooltip": ["borough", "approx_area_km2", "location_id"],
                                "color": {
                                    "field": "borough",
                                    "domain": ["Bronx", "Brooklyn", "EWR", "Manhattan", "Queens", "Staten Island"],
                                },
                            }
                        ],
                    },
                ),
                TableArtifactSpec(id=revenue_source.id, label="revenue-only detail", source_id=revenue_source.id),
                TableArtifactSpec(id=empty_source.id, label="empty table", source_id=empty_source.id),
                TableArtifactSpec(id=no_data_source.id, label="no-data message", source_id=no_data_source.id),
            ],
        ),
    )
    turn_output = TurnOutput(result.output, output_store)
    cards = asyncio.run(render_resolved_output(asyncio.run(turn_output.resolve()), pane_dir))
    pane.push(
        turn_payload(
            title="Answer controls preview",
            user="Compare top customers, with controls for the interpretation.",
            assistant=result.text,
            cards=cards,
            panel=pane_panel_for_output(result.output),
        ),
        turn_output=turn_output,
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
        card_payload(
            card_id=cards[i % len(cards)]["id"],
            artifact_id=f"many-card-{i}",
            label=label,
            views=cards[i % len(cards)]["views"],
        )
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


def _long_text_json_result() -> ResultCardInput:
    paragraph = (
        "This deliberately long paragraph exercises truncated table cells and the expanded text viewer. "
        "It should wrap naturally, preserve the complete value when opened, and remain easy to copy. "
    ) * 6
    multiline = "\n".join(
        f"Line {line:02d}: multiline content for dialog scrolling and preserved line breaks."
        for line in range(1, 25)
    )
    nested = {
        "request": {"id": "req-1042", "source": "preview", "flags": {"reviewed": True, "priority": False}},
        "items": [
            {"id": item, "name": f"item-{item:03d}", "tags": ["alpha", "beta"], "score": item / 10}
            for item in range(12)
        ],
    }
    large = {
        "metadata": {"fixture": "large-json", "count": 200},
        "records": [
            {"id": item, "status": ["ready", "review", "hold"][item % 3], "value": item * 17}
            for item in range(200)
        ],
    }
    df = pd.DataFrame(
        {
            "case": [
                "short text",
                "null",
                "long paragraph",
                "multiline text",
                "nested JSON string",
                "native dictionary",
                "native list",
                "wide JSON line",
                "invalid JSON-looking text",
                "large JSON document",
            ],
            "value": [
                "Short values should remain inline.",
                None,
                paragraph,
                multiline,
                json.dumps(nested),
                nested,
                ["alpha", 42, {"nested": True, "values": list(range(20))}],
                json.dumps({"id": 7, "note": "x" * 800, "enabled": True}),
                '{"broken": true, "message": "' + "invalid content " * 20 + '" trailing}',
                large,
            ],
        }
    )
    return _result_input(
        result_id="QDEBUG_LONG_TEXT_JSON",
        label="long_text_json",
        query="SELECT case, value FROM synthetic_text_cells ORDER BY case",
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
            title="Long text and JSON cells",
            user="Show representative long text and structured values in a table.",
            assistant=(
                "This table exercises inline truncation and expanded viewing for paragraphs, multiline text, "
                "JSON strings, native structures, wide lines, malformed JSON, and a larger document."
            ),
            result_inputs=[_long_text_json_result()],
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
            assistant="\n\n".join(
                [
                    _long_result_response(
                        "A standalone map card showing every supported geometry type from one query result. "
                        "The extended explanation makes this fixture useful for checking page scrolling before "
                        "the pointer reaches the interactive map."
                    )
                ]
                * 4
            ),
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
