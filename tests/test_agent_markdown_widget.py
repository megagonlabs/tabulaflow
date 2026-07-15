from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll

from tabulaflow.app.banner import COLOR_FLOW
from tabulaflow.app.widgets import AgentProgressWidget, AgentTextBlock, _make_agent_markdown_parser
from tabulaflow.chat import AnswerDelta, Finished
from tabulaflow.chat.result import ChatResult


class _AgentMarkdownApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.progress = AgentProgressWidget()

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = "#1a212c"
        return variables

    def compose(self) -> ComposeResult:
        yield VerticalScroll(self.progress, id="chat-log")


async def test_agent_answer_streams_as_markdown() -> None:
    markdown = """# Heading

This has **bold** and `code`.

- one
- two

---

| Name | Value |
|---|---:|
| A | 1 |

```python
print("hi")
```
"""
    app = _AgentMarkdownApp()

    async with app.run_test(size=(100, 30)) as pilot:
        await app.progress.apply(AnswerDelta(content=markdown[:40]))
        await app.progress.apply(AnswerDelta(content=markdown[40:]))
        await app.progress.apply(Finished(result=ChatResult(text=markdown)))
        await pilot.pause()

        block = app.progress._text_block
        assert isinstance(block, AgentTextBlock)
        assert len(block.query("MarkdownH1")) == 1
        assert len(block.query("MarkdownBulletList")) == 1
        assert [getattr(bullet, "symbol") for bullet in block.query("MarkdownBullet")] == ["- ", "- "]
        assert len(block.query("MarkdownHorizontalRule")) == 0
        assert len(block.query("MarkdownTable")) == 1
        assert len(block.query("MarkdownFence")) == 1


def test_agent_markdown_parser_supports_tables_without_raw_html_or_fuzzy_linkify() -> None:
    parser = _make_agent_markdown_parser()

    assert "<table>" in parser.render("| A | B |\n|---|---|\n| x | y |\n")
    assert "<s>x</s>" in parser.render("~~x~~")
    assert "<p>---</p>" in parser.render("---")
    assert "<hr" not in parser.render("---")
    assert "&lt;br&gt;" in parser.render("<br>")
    assert "<a href=" not in parser.render("https://example.com")
    assert '<a href="https://example.com">' in parser.render("<https://example.com>")


def test_agent_markdown_inline_code_uses_flow_color_without_background() -> None:
    assert f"color: {COLOR_FLOW};" in AgentTextBlock.DEFAULT_CSS
    assert "AgentTextBlock MarkdownBlock:dark > .code_inline" in AgentTextBlock.DEFAULT_CSS
    assert "background: transparent;" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_list_items_are_compact() -> None:
    assert "AgentTextBlock MarkdownBulletList Horizontal > Vertical > MarkdownParagraph" in AgentTextBlock.DEFAULT_CSS
    assert "AgentTextBlock MarkdownOrderedList Horizontal > Vertical > MarkdownParagraph" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_non_code_chrome_uses_text_color() -> None:
    assert "border-left: outer $foreground;" in AgentTextBlock.DEFAULT_CSS
    assert "keyline: thin $foreground;" in AgentTextBlock.DEFAULT_CSS
    assert f"color: {COLOR_FLOW};" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_fenced_code_is_flat() -> None:
    assert "AgentTextBlock MarkdownFence {\n        background: transparent;" in AgentTextBlock.DEFAULT_CSS
    assert "AgentTextBlock MarkdownFence > Label {\n        padding: 0;" in AgentTextBlock.DEFAULT_CSS
    assert "overflow: hidden hidden;" in AgentTextBlock.DEFAULT_CSS
    assert "scrollbar-size-horizontal: 0;" in AgentTextBlock.DEFAULT_CSS
    assert "text-wrap: wrap;" in AgentTextBlock.DEFAULT_CSS
