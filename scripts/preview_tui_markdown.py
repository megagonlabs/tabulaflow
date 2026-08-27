"""Preview TUI Markdown answer rendering.

    uv run scripts/preview_tui_markdown.py

Temporary visual fixture for checking ``AgentTextBlock`` styling without running
a real agent turn.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll

from tabulaflow.app.tui.theme import FOCUS_SURFACE
from tabulaflow.app.tui.widgets.progress import AgentProgressWidget
from tabulaflow.agents.chat import AnswerDelta, TurnFinished
from tabulaflow.agents.chat import ChatResult


MARKDOWN = """# Heading 1

## Heading 2

### Heading 3

#### Muted Heading 4

Paragraph text is written as plain text with a blank line between paragraphs.

This paragraph includes **bold text**, *italic text*, `inline code`, and ~~struck text~~.

---

Unordered list rendered with hyphen bullets:

- Item from dash source
* Item from star source
+ Item from plus source

- Item from dash source
- Item from star source
- Item from plus source

Nested list:

- Parent item
  - Child item
    - Grandchild item

Ordered list:

1. First item
2. Second item
3. Third item

> Blockquote with a neutral left border.
>
> Second quoted paragraph.

---

Markdown table with inline syntax:

| Case | Rendered Cell | Notes |
|---|---|---:|
| Inline styles | **bold** text, *italic* text, and `code_value` | 3 styles |
| Link | [docs](https://example.com/docs) | plain URL text |
| Autolink | <https://example.com/raw> | visible target |
| Image | ![diagram](https://example.com/diagram.png) | plain image text |
| Mixed | `customer_id` from [schema](https://example.com/schema) is **required** | combined |
| Long text | This cell has a deliberately long sentence to check wrapping, truncation, and the absence of hover tooltips in markdown table cells. | 1 |

Fenced code:

```python
def hello(name: str, customer_id: int, customer_name: str, region: str, lifetime_value: float, first_order_date: str, most_recent_order_date: str, preferred_channel: str, account_owner: str, renewal_probability: float) -> None:
    print(f"Hello, {name}")

long_sql = "SELECT customer_id, customer_name, region, lifetime_value, first_order_date, most_recent_order_date, preferred_channel, account_owner, renewal_probability, notes FROM analytics.customer_health_rollup WHERE region IN ('North America', 'Europe', 'Asia Pacific') ORDER BY lifetime_value DESC"

long_result = {"customer_id": 12345, "customer_name": "Example Customer With A Very Long Name", "recommended_action": "Schedule a renewal review, verify expansion opportunity, and compare support ticket trends before the next quarterly business review."}
```

Raw HTML is escaped: <br>

Link display cases:

- Explicit label: [docs](https://example.com/docs)
- URL autolink: <https://example.com/raw>
- Email autolink: <user@example.com>
- Label already equals destination: [https://example.com/same](https://example.com/same)
- Explicit mailto label: [email support](mailto:user@example.com)
- Inline code label: [`docs`](https://example.com/docs)
- Emphasized label: [**docs**](https://example.com/docs)

Image display cases:

- Image with alt text: ![diagram](https://example.com/diagram.png)
- Image without alt text: ![](https://example.com/no-alt.png)
- Alt already equals destination: ![https://example.com/same.png](https://example.com/same.png)

Bare URL should stay plain: https://example.com
"""


class TuiMarkdownPreview(App[None]):
    CSS_PATH = Path(__file__).resolve().parents[1] / "tabulaflow" / "app" / "tui" / "tui.tcss"

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = FOCUS_SURFACE
        return variables

    def compose(self) -> ComposeResult:
        yield VerticalScroll(AgentProgressWidget(), id="chat-log")

    async def on_mount(self) -> None:
        progress = self.query_one(AgentProgressWidget)
        midpoint = len(MARKDOWN) // 2
        await progress.apply(AnswerDelta(content=MARKDOWN[:midpoint]))
        await progress.apply(AnswerDelta(content=MARKDOWN[midpoint:]))
        await progress.apply(TurnFinished(result=ChatResult(text=MARKDOWN)))


if __name__ == "__main__":
    TuiMarkdownPreview().run()
