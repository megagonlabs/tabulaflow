"""Compare code highlighting paths.

Run:
    uv run scripts/preview_code_highlighting_paths.py

This opens a TUI preview for terminal-rendered paths and writes a browser-pane
HTML fixture to ``/tmp/tabulaflow_code_highlighting_paths.html``.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from tempfile import gettempdir
from typing import TypedDict

from rich.console import RenderableType
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Label, Static, TextArea

from tabulaflow.app.display import build_query
from tabulaflow.app.pane.cards import build_query_data
from tabulaflow.app.theme import (
    CODE_TEXT,
    FOCUS_SURFACE,
    KEY_HINT,
    configure_code_text_area,
)
from tabulaflow.app.widgets import AgentTextBlock


class CodeSample(TypedDict):
    title: str
    lexer: str
    text_area_language: str
    code: str


PYTHON_CODE = """\
#!/usr/bin/env python3
# Preview: comments, decorators, classes, builtins, numbers, strings, exceptions.
from __future__ import annotations

import asyncio
import re as regex
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, ClassVar, Final, Literal, TypeAlias

SCORE_FLOOR: Final[float] = 1_000.50
Region: TypeAlias = Literal["NA", "EU", "APAC"]
PATTERN = regex.compile(r"(?P<name>[A-Z][\\w-]+)\\s+#(?P<id>\\d+)")
RAW_BYTES = b"\\x00\\xff"


@dataclass(slots=True)
class CustomerRanker:
    '''Docstring with single quotes so the fixture remains readable.'''

    weights: dict[str, Decimal] = field(default_factory=dict)
    default_region: ClassVar[str] = "NA"

    @classmethod
    def from_rows(cls, rows: Iterable[dict[str, Any]]) -> "CustomerRanker":
        return cls(weights={str(row["customer_id"]): Decimal("1.25") for row in rows})

    async def rank_customers(
        self,
        customers: list[dict[str, object]],
        min_lifetime_value: float = SCORE_FLOOR,
        preferred_regions: set[Region] | None = None,
    ) -> list[dict[str, object]]:
        preferred_regions = preferred_regions or {"NA", "EU"}
        scored: list[dict[str, object]] = []
        for index, customer in enumerate(customers, start=1):
            region = str(customer.get("region", self.default_region))
            lifetime_value = float(customer.get("lifetime_value") or 0)
            boost = self.weights.get(str(customer["customer_id"]), Decimal("0.0"))
            if lifetime_value >= min_lifetime_value and region in preferred_regions:
                score = lifetime_value * 0.82 + float(boost) + len(region) * 3.5
                scored.append(
                    {
                        "customer_id": customer["customer_id"],
                        "name": customer["name"],
                        "score": score,
                        "rank_label": f"{index=:03d} {region=} {score=:.2f}",
                    }
                )
            elif region not in preferred_regions:
                continue
            else:
                break
        return sorted(scored, key=lambda row: row["score"], reverse=True)


async def main() -> None:
    sample = [{"customer_id": 42, "name": "ACME", "region": "NA", "lifetime_value": 250_000}]
    try:
        ranker = CustomerRanker.from_rows(sample)
        result = await ranker.rank_customers(sample)
    except (KeyError, ValueError) as exc:
        raise RuntimeError("bad customer payload") from exc
    finally:
        print(result if "result" in locals() else None)


if __name__ == "__main__":
    asyncio.run(main())

# Deliberately invalid Python fragment to preview Token.Error styling.
invalid_token_preview = $not_python
"""


SQL_CODE = """\
-- Preview: comments, DDL, DML, CTEs, joins, casts, windows, strings, numbers.
CREATE TEMP TABLE IF NOT EXISTS analytics.customer_stage (
    customer_id BIGINT PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    region TEXT DEFAULT 'NA',
    lifetime_value NUMERIC(18, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

/* Upsert example with quoted identifiers and typed literals. */
INSERT INTO analytics.customer_stage AS target (
    customer_id,
    customer_name,
    region,
    lifetime_value,
    is_active,
    created_at
)
VALUES
    (42, 'ACME', 'NA', 250000.75, TRUE, TIMESTAMP '2026-01-15 09:30:00'),
    (84, 'Globex', 'EU', 98000.00, FALSE, CURRENT_TIMESTAMP)
ON CONFLICT (customer_id) DO UPDATE
SET
    customer_name = EXCLUDED.customer_name,
    lifetime_value = COALESCE(EXCLUDED.lifetime_value, target.lifetime_value);

WITH customer_health AS (
    SELECT
        c.customer_id,
        c.customer_name,
        "Account Owner" AS account_owner,
        c.region,
        CAST(SUM(o.net_revenue) AS DECIMAL(18, 2)) AS lifetime_value,
        MAX(o.order_date)::DATE AS most_recent_order_date,
        COUNT(*) FILTER (WHERE t.status = 'open') AS open_ticket_count,
        AVG(o.net_revenue) OVER (
            PARTITION BY c.region
            ORDER BY MAX(o.order_date) DESC
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS rolling_region_revenue
    FROM analytics.customers AS c
    LEFT JOIN analytics.orders AS o
        ON o.customer_id = c.customer_id
    LEFT JOIN support.tickets AS t
        ON t.customer_id = c.customer_id
    WHERE c.region IN ('NA', 'EU', 'APAC')
      AND o.order_date >= DATE '2025-01-01' - INTERVAL '30 days'
      AND c.customer_name LIKE 'A%' ESCAPE '\\'
      AND c.deleted_at IS NULL
    GROUP BY 1, 2, 3, 4
    HAVING SUM(o.net_revenue) > 1e5
)
SELECT
    customer_id,
    customer_name,
    region,
    lifetime_value,
    rolling_region_revenue,
    most_recent_order_date,
    CASE
        WHEN open_ticket_count > 5 THEN 'support_risk'
        WHEN lifetime_value BETWEEN 100000 AND 999999.99 THEN 'expansion_candidate'
        ELSE 'monitor'
    END AS recommended_action
FROM customer_health
WHERE NOT (region = 'APAC' AND lifetime_value < 50000)
ORDER BY lifetime_value DESC, most_recent_order_date DESC;

-- Deliberately unsupported placeholder syntax to preview Token.Error styling.
SELECT $1 AS positional_parameter_preview;
"""


SAMPLES: tuple[CodeSample, ...] = (
    {
        "title": "Python",
        "lexer": "python",
        "text_area_language": "python",
        "code": PYTHON_CODE,
    },
    {
        "title": "SQL",
        "lexer": "sql",
        "text_area_language": "sql",
        "code": SQL_CODE,
    },
)


OUTPUT_HTML = Path(gettempdir()) / "tabulaflow_code_highlighting_paths.html"


def _pane_query_html(sample: CodeSample) -> str:
    query = build_query_data(sample["code"], lexer=sample["lexer"])["query"]
    return (
        '<section class="tf-view tf-query-view">'
        '<section class="query-card">'
        '<div class="query-bar">'
        f'<span class="query-lang">{escape(str(query["language"]))}</span>'
        '<button class="query-copy" type="button" aria-label="Copy query" title="Copy query">'
        '<span class="copy-icon" aria-hidden="true"></span>'
        "</button>"
        "</div>"
        f'{query["html"]}'
        "</section>"
        "</section>"
    )


def write_browser_fixture(path: Path = OUTPUT_HTML) -> Path:
    cards = "\n".join(
        f"<h2>{escape(sample['title'])}</h2>\n{_pane_query_html(sample)}"
        for sample in SAMPLES
    )
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TabulaFlow code highlighting paths</title>
<style>
:root {{
  --bg: #0f1117;
  --card: #1a212c;
  --text: #e4e4e7;
  --text-muted: #6a737d;
  --accent: #3eb489;
  --query-bg: #151922;
  --query-border: #242b36;
  --query-hover: #202633;
}}
body {{
  margin: 0;
  padding: 28px;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
main {{
  max-width: 1120px;
  margin: 0 auto;
}}
h1 {{
  margin: 0 0 6px;
  font-size: 18px;
}}
h2 {{
  margin: 28px 0 10px;
  color: var(--text);
  font-size: 14px;
}}
p {{
  margin: 0 0 18px;
  color: var(--text-muted);
}}
.query-card {{
  background: var(--query-bg);
  color: var(--text);
  border-radius: 10px;
  overflow: hidden;
}}
.query-bar {{
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px 0 18px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--query-border);
  color: #f5f5f5;
  font: 600 13px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.query-copy {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 30px;
  width: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #f5f5f5;
}}
.query-copy:hover {{
  background: var(--query-hover);
}}
.copy-icon {{
  position: relative;
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}}
.copy-icon::before,
.copy-icon::after {{
  content: "";
  position: absolute;
  width: 10px;
  height: 12px;
  border: 2px solid currentColor;
  border-radius: 4px;
  box-sizing: border-box;
}}
.copy-icon::before {{
  left: 1px;
  top: 4px;
  opacity: 0.72;
}}
.copy-icon::after {{
  left: 5px;
  top: 0;
  background: var(--query-bg);
}}
.tf-query-view .highlight {{
  margin: 0;
  background: var(--query-bg) !important;
}}
.tf-query-view .highlight pre {{
  margin: 0;
  padding: 18px 20px 20px;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--query-bg) !important;
  font: 13px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
}}
</style>
</head>
<body>
<main>
<h1>Browser pane query rendering</h1>
<p>This fixture uses the current browser-pane query path: Pygments + HtmlFormatter(style=TabulaflowPygmentsStyle, noclasses=True). Neutral code text: {CODE_TEXT}.</p>
{cards}
</main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return path


def _heading(text: str) -> Static:
    label = Text(text, style="bold")
    return Static(label, classes="path-heading")


def _description(text: str) -> Static:
    return Static(Text(text, style="dim"), classes="path-description")


def _rich_preview(sample: CodeSample) -> RenderableType:
    return build_query(
        sample["code"],
        max_lines=None,
        lexer=sample["lexer"],
        line_numbers=True,
    )


class CodeHighlightingPathsPreview(App[None]):
    CSS_PATH = Path(__file__).resolve().parents[1] / "tabulaflow" / "app" / "tui.tcss"

    CSS = """
    CodeHighlightingPathsPreview {
        background: $background;
    }

    #preview-root {
        padding: 1 2;
    }

    .intro {
        margin: 0 0 1 0;
        color: $foreground;
    }

    .sample-section {
        margin: 1 0 2 0;
        height: auto;
    }

    .sample-title {
        margin: 0 0 1 0;
        color: $foreground;
        text-style: bold;
    }

    .path-heading {
        margin: 1 0 0 0;
        color: $foreground;
    }

    .path-description {
        margin: 0 0 1 0;
    }

    .code-textarea {
        height: 24;
        margin: 0 0 1 0;
        border: solid white;
        background: $background;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    .rich-preview {
        margin: 0 0 1 0;
    }

    .browser-path {
        margin: 0 0 1 0;
        color: $foreground;
    }
    """

    def __init__(self, browser_fixture: Path) -> None:
        super().__init__()
        self._browser_fixture = browser_fixture

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = FOCUS_SURFACE
        return variables

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="preview-root"):
            yield Static(
                f"Code highlighting comparison with neutral code text {CODE_TEXT}. "
                "Open the generated HTML file separately for the browser-pane path.",
                classes="intro",
            )
            yield Static(f"Browser pane fixture: {self._browser_fixture}", classes="browser-path")
            for sample in SAMPLES:
                with Vertical(classes="sample-section"):
                    yield Label(sample["title"], classes="sample-title")

                    yield _heading("1. TUI assistant markdown fenced code")
                    yield _description("AgentTextBlock → MarkdownFence → textual.highlight.HighlightTheme")
                    yield AgentTextBlock(f"```{sample['lexer']}\n{sample['code']}\n```")

                    yield _heading("2. TUI cell/query browser")
                    yield _description("TextArea → configure_code_text_area()")
                    yield TextArea(
                        sample["code"],
                        language=sample["text_area_language"],
                        read_only=True,
                        show_line_numbers=True,
                        soft_wrap=True,
                        classes="code-textarea",
                    )

                    yield _heading("3. Rich query preview")
                    yield _description("build_query() → Rich Syntax(theme=TABULAFLOW_RICH_SYNTAX_THEME)")
                    yield Static(_rich_preview(sample), classes="rich-preview")

                    yield _heading("4. Browser output pane query card")
                    yield _description("build_query_data() → Pygments HtmlFormatter(style=TabulaflowPygmentsStyle). See generated HTML file.")

    def on_mount(self) -> None:
        for text_area in self.query(TextArea):
            configure_code_text_area(text_area)


def main() -> None:
    browser_fixture = write_browser_fixture()
    print(f"Browser pane fixture: {browser_fixture}")
    print(f"Open in browser: {browser_fixture.as_uri()}")
    print(f"Quit TUI: {KEY_HINT}Esc[/] or Ctrl+C")
    CodeHighlightingPathsPreview(browser_fixture).run()


if __name__ == "__main__":
    main()
