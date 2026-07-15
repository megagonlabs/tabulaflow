from __future__ import annotations

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll

from tabulaflow.app.banner import COLOR_FLOW
from tabulaflow.app.theme import (
    CODE_FUNCTION,
    CODE_KEYWORD,
    CODE_NUMBER,
    CODE_STRING,
    CODE_TEXT,
    TabulaflowCodeHighlightTheme,
)
from tabulaflow.app.widgets import (
    AgentMarkdownFence,
    AgentProgressWidget,
    AgentTextBlock,
    _make_agent_markdown_parser,
)
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
    assert "margin: 0 0 1 0;" in AgentTextBlock.DEFAULT_CSS
    assert "AgentTextBlock MarkdownFence > Label {\n        padding: 0;" in AgentTextBlock.DEFAULT_CSS
    assert "overflow: hidden hidden;" in AgentTextBlock.DEFAULT_CSS
    assert "scrollbar-size-horizontal: 0;" in AgentTextBlock.DEFAULT_CSS
    assert "text-wrap: wrap;" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_fenced_code_does_not_underline_functions() -> None:
    assert AgentTextBlock.BLOCKS["fence"] is AgentMarkdownFence
    content = AgentMarkdownFence.highlight("def hello(name: str) -> None:\n    pass", "python")
    function_styles = [
        str(span.style)
        for span in content._spans
        if content.plain[span.start : span.end] == "hello"
    ]
    assert function_styles
    assert all("underline" not in style for style in function_styles)
    assert all(style == CODE_FUNCTION for style in function_styles)


def test_agent_markdown_fenced_code_identifiers_use_foreground() -> None:
    content = AgentMarkdownFence.highlight("customer_id = customer['id']", "python")
    identifier_styles = [
        str(span.style)
        for span in content._spans
        if content.plain[span.start : span.end] == "customer_id"
    ]
    assert identifier_styles
    assert all(style == CODE_TEXT for style in identifier_styles)


def test_agent_markdown_fenced_code_keywords_use_text_primary() -> None:
    content = AgentMarkdownFence.highlight(
        "from pathlib import Path\nif active and score in scores:\n    return score",
        "python",
    )
    keyword_styles = [
        str(span.style)
        for span in content._spans
        if content.plain[span.start : span.end] in {"from", "import", "if", "and", "in", "return"}
    ]
    assert keyword_styles
    assert all(style == CODE_KEYWORD for style in keyword_styles)


def test_agent_markdown_fenced_code_numbers_use_distinct_violet() -> None:
    content = AgentMarkdownFence.highlight("score = 0.82 + 3", "python")
    number_styles = [
        str(span.style)
        for span in content._spans
        if content.plain[span.start : span.end] in {"0.82", "3"}
    ]
    assert number_styles
    assert all(style == CODE_NUMBER for style in number_styles)


def test_agent_markdown_fenced_code_error_tokens_use_foreground() -> None:
    content = AgentMarkdownFence.highlight("invalid_token_preview = $not_python", "python")
    error_styles = [
        str(span.style)
        for span in content._spans
        if content.plain[span.start : span.end] == "$"
    ]
    assert error_styles
    assert all(style == CODE_TEXT for style in error_styles)


def test_agent_markdown_fenced_code_strings_use_double_string_green() -> None:
    content = AgentMarkdownFence.highlight(
        '"""doc"""\nactive = True\nvalue = "double" + b"bytes" + f"{active=}"',
        "python",
    )
    styles_by_text = {
        content.plain[span.start : span.end]: str(span.style)
        for span in content._spans
    }
    assert styles_by_text['"""doc"""'] == f"italic {CODE_STRING}"
    assert styles_by_text["True"] == CODE_STRING
    assert styles_by_text["double"] == CODE_STRING
    assert styles_by_text["b"] == CODE_STRING
    assert styles_by_text["bytes"] == CODE_STRING
    assert styles_by_text["f"] == CODE_STRING


def test_agent_markdown_fenced_code_uses_no_bold_token_styles() -> None:
    samples = [
        (
            "python",
            """
from pathlib import Path

@decorator
class Example:
    def method(self) -> None:
        score = 0.82 + 3
        return True
""",
        ),
        (
            "sql",
            """
SELECT COUNT(*) AS total
FROM analytics.table
WHERE amount > 1 AND status = 'ok';
""",
        ),
    ]
    for lexer, code in samples:
        for token, value in lex(code, get_lexer_by_name(lexer)):
            if not value.strip():
                continue
            cur = token
            while cur is not Token:
                if cur in TabulaflowCodeHighlightTheme.STYLES:
                    assert "bold" not in TabulaflowCodeHighlightTheme.STYLES[cur].split()
                    break
                cur = cur.parent
