from __future__ import annotations

from pygments.token import Token
from rich.color import Color
from rich.syntax import PygmentsSyntaxTheme

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
