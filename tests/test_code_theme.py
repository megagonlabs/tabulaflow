from __future__ import annotations

from pygments.token import Token
from rich.color import Color
from rich.syntax import PygmentsSyntaxTheme
from textual.app import App, ComposeResult
from textual.widgets import TextArea

from tabulaflow.app.theme import (
    CODE_COMMENT,
    CODE_FUNCTION,
    CODE_KEYWORD,
    CODE_NUMBER,
    CODE_STRING,
    CODE_TEXT,
    CODE_TYPE,
    TABULAFLOW_CODE_TEXT_AREA_THEME,
    TabulaflowCodeHighlightTheme,
    TabulaflowPygmentsStyle,
    configure_code_text_area,
)


def _hex(color: Color | None) -> str:
    assert color is not None
    assert color.triplet is not None
    return f"#{color.triplet.red:02X}{color.triplet.green:02X}{color.triplet.blue:02X}"


def test_code_theme_pygments_and_markdown_fence_tokens_share_palette() -> None:
    rich_theme = PygmentsSyntaxTheme(TabulaflowPygmentsStyle)

    pairs = [
        (Token.Comment, CODE_COMMENT),
        (Token.Error, CODE_TEXT),
        (Token.Keyword, CODE_KEYWORD),
        (Token.Keyword.Constant, CODE_STRING),
        (Token.Name.Function, CODE_FUNCTION),
        (Token.Name.Builtin, CODE_TYPE),
        (Token.Literal.Number, CODE_NUMBER),
        (Token.Literal.String, CODE_STRING),
        (Token.Operator, CODE_TEXT),
        (Token.Operator.Word, CODE_KEYWORD),
    ]
    for token, color in pairs:
        assert TabulaflowCodeHighlightTheme.STYLES[token] == color
        assert _hex(rich_theme.get_style_for_token(token).color) == color


def test_code_text_area_theme_uses_shared_palette_without_bold_syntax_styles() -> None:
    styles = TABULAFLOW_CODE_TEXT_AREA_THEME.syntax_styles

    assert _hex(styles["keyword"].color) == CODE_KEYWORD
    assert _hex(styles["function"].color) == CODE_FUNCTION
    assert _hex(styles["string"].color) == CODE_STRING
    assert _hex(styles["number"].color) == CODE_NUMBER
    assert _hex(styles["type"].color) == CODE_TYPE
    assert _hex(styles["comment"].color) == CODE_COMMENT
    assert all(style.bold is not True for style in styles.values())


async def test_code_text_area_sql_numbers_are_not_captured_as_strings() -> None:
    sql = "SELECT CASE WHEN verified_purchase = 1 THEN 'yes' ELSE 0 END AS flag, 3.14 AS score"

    class _SqlTextAreaApp(App[None]):
        def compose(self) -> ComposeResult:
            yield TextArea(sql, language="sql")

        def on_mount(self) -> None:
            configure_code_text_area(self.query_one(TextArea))

    app = _SqlTextAreaApp()
    async with app.run_test(size=(100, 20)) as pilot:
        await pilot.pause()
        text_area = app.query_one(TextArea)
        text_area._build_highlight_map()  # noqa: SLF001
        highlights = {
            sql[start : end if end else len(sql)]: highlight_name
            for spans in text_area._highlights.values()  # noqa: SLF001
            for start, end, highlight_name in spans
        }

    assert highlights["1"] == "number"
    assert highlights["0"] == "number"
    assert highlights["3.14"] == "float"
    assert highlights["'yes'"] == "string"
