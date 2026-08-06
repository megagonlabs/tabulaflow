from __future__ import annotations

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token
from rich.segment import Segment
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.content import Content
from textual.geometry import Offset
from textual.selection import Selection
from textual.strip import Strip
from textual.widgets._markdown import MarkdownParagraph, MarkdownTableCellContents

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
    FrozenAgentTextBlock,
    _make_agent_markdown_parser,
    _strips_to_text,
)
from tabulaflow.chat import AnswerDelta


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


def test_agent_markdown_blocks_are_selectable() -> None:
    assert AgentTextBlock.ALLOW_SELECT is True
    assert FrozenAgentTextBlock.ALLOW_SELECT is True


def test_frozen_markdown_selection_uses_snapshot_text() -> None:
    block = FrozenAgentTextBlock(
        [Strip([Segment("Hello world")]), Strip([Segment("Second line")])],
        width=20,
    )

    result = block.get_selection(Selection.from_offsets(Offset(6, 0), Offset(6, 1)))
    assert result is not None
    selected, ending = result

    assert selected == "world\nSecond"
    assert ending == "\n"


def test_frozen_markdown_text_snapshot_trims_padding() -> None:
    text = _strips_to_text([Strip([Segment("Hello"), Segment("   ")])])

    assert text.plain == "Hello"


async def test_agent_answer_streams_as_markdown() -> None:
    markdown = """# Heading

This has **bold** and `code`.

- one
- two

---

| Name | Value |
|---|---:|
| A | [docs](https://example.com/docs) |

```python
print("hi")
```
"""
    app = _AgentMarkdownApp()

    async with app.run_test(size=(100, 30)) as pilot:
        await app.progress.apply(AnswerDelta(content=markdown[:40]))
        await app.progress.apply(AnswerDelta(content=markdown[40:]))
        await pilot.pause()

        block = app.progress._text_block
        assert isinstance(block, AgentTextBlock)
        assert len(block.query("MarkdownH1")) == 1
        assert len(block.query("MarkdownBulletList")) == 1
        assert [getattr(bullet, "symbol") for bullet in block.query("MarkdownBullet")] == ["- ", "- "]
        assert len(block.query("MarkdownHorizontalRule")) == 0
        assert len(block.query("MarkdownTable")) == 1
        table_cells = list(block.query(MarkdownTableCellContents))
        assert table_cells
        assert all(cell.tooltip is None for cell in table_cells)
        for cell in table_cells:
            content = cell.content
            assert isinstance(content, Content)
            assert all("@click" not in str(span.style) for span in content._spans)
        assert len(block.query("MarkdownFence")) == 1


async def test_agent_markdown_links_show_visible_destinations() -> None:
    markdown = (
        "See [docs](https://example.com/docs), <https://example.com/raw>, "
        "<user@example.com>, [https://example.com/same](https://example.com/same), "
        "[email support](mailto:user@example.com), [`docs`](https://example.com/docs), "
        "[**docs**](https://example.com/docs), and ![diagram](https://example.com/diagram.png)."
    )
    app = _AgentMarkdownApp()

    async with app.run_test(size=(120, 20)) as pilot:
        await app.progress.apply(AnswerDelta(content=markdown))
        await pilot.pause()

        block = app.progress._text_block
        assert isinstance(block, AgentTextBlock)
        paragraph = block.query_one(MarkdownParagraph)
        assert paragraph._content.plain == (
            "See docs (https://example.com/docs), https://example.com/raw, "
            "user@example.com, https://example.com/same, "
            "email support (mailto:user@example.com), docs (https://example.com/docs), "
            "docs (https://example.com/docs), and diagram (https://example.com/diagram.png)."
        )
        assert all("@click" not in str(span.style) for span in paragraph._content._spans)


async def test_interrupted_answer_freezes_to_selectable_snapshot() -> None:
    app = _AgentMarkdownApp()

    async with app.run_test(size=(80, 20)) as pilot:
        await app.progress.apply(AnswerDelta(content="Partial answer text"))
        await pilot.pause()

        await app.progress.mark_interrupted()
        await pilot.pause()

        assert app.progress._text_block is None
        frozen = list(app.query(FrozenAgentTextBlock))
        assert len(frozen) == 1
        result = frozen[0].get_selection(Selection.from_offsets(Offset(1, 0), Offset(8, 0)))
        assert result is not None
        assert result[0] == "Partial"


def test_agent_markdown_parser_supports_tables_without_raw_html_or_fuzzy_linkify() -> None:
    parser = _make_agent_markdown_parser()

    assert "<table>" in parser.render("| A | B |\n|---|---|\n| x | y |\n")
    assert "<p>~~x~~</p>" in parser.render("~~x~~")
    assert "<s>" not in parser.render("~~x~~")
    assert "<p>---</p>" in parser.render("---")
    assert "<hr" not in parser.render("---")
    assert "&lt;br&gt;" in parser.render("<br>")
    assert "<a href=" not in parser.render("https://example.com")
    assert "<a href=" not in parser.render("<https://example.com>")
    assert "<p>docs (https://example.com/docs)</p>" in parser.render("[docs](https://example.com/docs)")
    assert "<img" not in parser.render("![diagram](https://example.com/diagram.png)")
    assert "<p>diagram (https://example.com/diagram.png)</p>" in parser.render(
        "![diagram](https://example.com/diagram.png)"
    )


def test_agent_markdown_inline_code_uses_function_color_without_background() -> None:
    assert f"color: {CODE_FUNCTION};" in AgentTextBlock.DEFAULT_CSS
    assert "AgentTextBlock MarkdownBlock:dark > .code_inline" in AgentTextBlock.DEFAULT_CSS
    assert "background: transparent;" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_list_items_are_compact() -> None:
    assert "AgentTextBlock MarkdownBulletList Horizontal > Vertical > MarkdownParagraph" in AgentTextBlock.DEFAULT_CSS
    assert "AgentTextBlock MarkdownOrderedList Horizontal > Vertical > MarkdownParagraph" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_non_code_chrome_uses_text_color() -> None:
    assert "border-left: vkey $foreground;" in AgentTextBlock.DEFAULT_CSS
    assert "keyline: thin $foreground;" in AgentTextBlock.DEFAULT_CSS
    assert f"color: {CODE_FUNCTION};" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_fenced_code_is_flat() -> None:
    assert "AgentTextBlock MarkdownFence {\n        background: transparent;" in AgentTextBlock.DEFAULT_CSS
    assert f"color: {CODE_TEXT};" in AgentTextBlock.DEFAULT_CSS
    assert "margin: 0 0 1 2;" in AgentTextBlock.DEFAULT_CSS
    assert "AgentTextBlock MarkdownFence > Label {\n        padding: 0;" in AgentTextBlock.DEFAULT_CSS
    assert "overflow: hidden hidden;" in AgentTextBlock.DEFAULT_CSS
    assert "scrollbar-size-horizontal: 0;" in AgentTextBlock.DEFAULT_CSS
    assert "text-wrap: wrap;" in AgentTextBlock.DEFAULT_CSS


def test_agent_markdown_fenced_code_does_not_underline_functions() -> None:
    assert AgentTextBlock.BLOCKS["fence"] is AgentMarkdownFence
    content = AgentMarkdownFence.highlight("def hello(name: str) -> None:\n    pass", "python")
    function_styles = [str(span.style) for span in content._spans if content.plain[span.start : span.end] == "hello"]
    assert function_styles
    assert all("underline" not in style for style in function_styles)
    assert all(style == CODE_FUNCTION for style in function_styles)


def test_agent_markdown_fenced_code_identifiers_use_foreground() -> None:
    content = AgentMarkdownFence.highlight("customer_id = customer['id']", "python")
    identifier_styles = [
        str(span.style) for span in content._spans if content.plain[span.start : span.end] == "customer_id"
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
        str(span.style) for span in content._spans if content.plain[span.start : span.end] in {"0.82", "3"}
    ]
    assert number_styles
    assert all(style == CODE_NUMBER for style in number_styles)


def test_agent_markdown_fenced_code_error_tokens_use_foreground() -> None:
    content = AgentMarkdownFence.highlight("invalid_token_preview = $not_python", "python")
    error_styles = [str(span.style) for span in content._spans if content.plain[span.start : span.end] == "$"]
    assert error_styles
    assert all(style == CODE_TEXT for style in error_styles)


def test_agent_markdown_fenced_code_unclassified_tokens_use_code_text() -> None:
    samples = [
        ("text", "plain prose in a code fence"),
        ("markdown", "# Heading\n\n**bold** [link](https://example.com)"),
        ("yaml", "name: Alice\nactive: true\ncount: 3"),
    ]
    for language, code in samples:
        content = AgentMarkdownFence.highlight(code, language)
        visible_styles = [str(span.style) for span in content._spans if content.plain[span.start : span.end].strip()]
        assert visible_styles
        assert "$text" not in visible_styles
        assert CODE_TEXT in visible_styles


def test_agent_markdown_fenced_code_strings_use_double_string_green() -> None:
    content = AgentMarkdownFence.highlight(
        '"""doc"""\nactive = True\nvalue = "double" + b"bytes" + f"{active=}"',
        "python",
    )
    styles_by_text = {content.plain[span.start : span.end]: str(span.style) for span in content._spans}
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
