"""CLI theme constants."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

from pygments.style import Style as PygmentsStyle
from pygments.token import Token
from rich.style import Style
from rich.syntax import PygmentsSyntaxTheme
from textual.highlight import HighlightTheme
from textual.widgets.text_area import TextAreaTheme

if TYPE_CHECKING:
    from textual.widgets import TextArea

ACCENT = "#3EB489"  # mint
ACCENT_BOLD = f"bold {ACCENT}"
ACCENT_RGB = (62, 180, 137)  # mint (RGB)

# Project repository — shown in the TUI banner and browser output pane.
GITHUB_SLUG = "megagonlabs/tabulaflow"
GITHUB_URL = f"https://github.com/{GITHUB_SLUG}"

# Error / danger red. An explicit hex (not the named ``red``) on purpose: Rich
# resolves ``red`` to (128,0,0) but Textual resolves it to (255,0,0), so the same
# ``[red]`` markup rendered via the two paths produced two different shades. The one
# canonical value: use ``style=ERROR`` in code, or ``f"[{ERROR}]…[/]"`` in markup.
ERROR = "#ff7777"

# git diffstat token colors in tool-progress labels (e.g. "Edit foo +5 -2"):
# additions in green, removals in red. git's own default defers to the terminal's
# ANSI green/red (no fixed hex); we pin GitHub's diff palette — bright, tuned for a
# dark background — rather than the named ``green``/``red`` (which Rich and Textual
# resolve to different shades, see ERROR above).
DIFF_ADDED = "#3FB950"
DIFF_REMOVED = "#F85149"

# Grey shade for inactive/unfocused states of widgets that normally
# display mint accents (record pill bg, view stepper chevrons / label in
# an unfocused AgentResultWidget). Matches the exact color Textual
# resolves Rich's ``dim`` attribute to (``#999999``), so the unfocused
# pill / view stepper sit in the same visual register as the dim hint
# labels. Conveniently, ~6.4:1 contrast against black — well above the
# terminal min-contrast threshold that would otherwise cause black pill
# text to auto-flip to a brighter shade.
ACCENT_DIM = "#999999"

# Column key markers in the schema browser tree / column-detail tables.
# PK rides the mint accent (it's the structurally important marker); FK uses
# the dim grey so it reads as secondary without introducing an off-palette hue.
PK_MARKER = ACCENT_BOLD
FK_MARKER = f"bold {ACCENT_DIM}"

# Background shade for focused/active interactive surfaces (focused
# AgentResultWidget, focused input bar, focused/hovered explorer button).
# Slightly lighter than ``$surface`` so the focused element pops out
# without needing a border. Exposed to CSS as ``$focus-surface`` via
# ``TabulaflowApp.get_css_variables``.
FOCUS_SURFACE = "#2D2D2D"

# Background shade for settled raised content (the user-message band). A gentle
# lift that sits *between* ``$surface`` and ``FOCUS_SURFACE`` so user messages
# read as distinct-but-passive — and the focused surface stays the brightest,
# uniquely-active tone above them.
MESSAGE_SURFACE = "#252525"

# Color used for keyboard-key glyphs in hint bars (e.g. "Esc", "Enter", "[/]").
# Kept separate from ACCENT so the two can evolve independently.
KEY_HINT_COLOR = "#3EB489"  # "#9EC8B2"
KEY_HINT = f"bold {KEY_HINT_COLOR}"
# Inactive hint keys use the same ``"dim"`` foreground as their labels so
# the colors match exactly (e.g. "Enter" and "Inspect" share a color), but
# keep ``bold`` so the key glyph is still distinguishable from the label
# text by weight.
KEY_HINT_DIM = "bold dim"


CODE_TEXT = "#E0E0E0"
CODE_COMMENT = "#8A8A8A"
CODE_KEYWORD = "#57A5E2"
CODE_FUNCTION = "#78DCE8"
CODE_STRING = "#7EC193"
CODE_NUMBER = "#C792EA"
CODE_TYPE = "#FFC473"

_TEXTUAL_SQL_HIGHLIGHT_QUERY = (
    files("textual").joinpath("tree-sitter", "highlights", "sql.scm").read_text(encoding="utf-8")
)
TABULAFLOW_SQL_HIGHLIGHT_QUERY = _TEXTUAL_SQL_HIGHLIGHT_QUERY.replace(
    "\n(literal) @string\n",
    "\n((literal) @string\n  (#match? @string \"^'.*'$\"))\n",
).replace(
    '"^[-+]?%d+$"',
    '"^[-+]?[0-9]+$"',
).replace(
    '"^[-+]?%d*\\.%d*$"',
    '"^[-+]?[0-9]*\\.[0-9]+$"',
)


class TabulaflowCodeHighlightTheme(HighlightTheme):
    """Textual MarkdownFence syntax theme."""

    STYLES = {
        Token.Comment: CODE_COMMENT,
        Token.Error: CODE_TEXT,
        Token.Keyword: CODE_KEYWORD,
        Token.Keyword.Constant: CODE_STRING,
        Token.Keyword.Namespace: CODE_KEYWORD,
        Token.Literal.Number: CODE_NUMBER,
        Token.Literal.String: CODE_STRING,
        Token.Literal.String.Doc: f"italic {CODE_STRING}",
        Token.Literal.String.Double: CODE_STRING,
        Token.Name: CODE_TEXT,
        Token.Name.Builtin: CODE_TYPE,
        Token.Name.Builtin.Pseudo: CODE_TEXT,
        Token.Name.Class: CODE_TYPE,
        Token.Name.Decorator: CODE_KEYWORD,
        Token.Name.Exception: CODE_TEXT,
        Token.Name.Function: CODE_FUNCTION,
        Token.Name.Function.Magic: CODE_FUNCTION,
        Token.Name.Namespace: CODE_TEXT,
        Token.Name.Variable: CODE_TEXT,
        Token.Operator: CODE_TEXT,
        Token.Operator.Word: CODE_KEYWORD,
        Token.Punctuation: CODE_TEXT,
        Token.Whitespace: "",
    }


class TabulaflowPygmentsStyle(PygmentsStyle):  # type: ignore[misc]
    """Pygments syntax theme for Rich previews."""

    background_color = None
    styles = {
        Token.Comment: CODE_COMMENT,
        Token.Error: CODE_TEXT,
        Token.Keyword: CODE_KEYWORD,
        Token.Keyword.Constant: CODE_STRING,
        Token.Keyword.Namespace: CODE_KEYWORD,
        Token.Literal.Number: CODE_NUMBER,
        Token.Literal.String: CODE_STRING,
        Token.Literal.String.Doc: f"italic {CODE_STRING}",
        Token.Literal.String.Double: CODE_STRING,
        Token.Name: CODE_TEXT,
        Token.Name.Builtin: CODE_TYPE,
        Token.Name.Builtin.Pseudo: CODE_TEXT,
        Token.Name.Class: CODE_TYPE,
        Token.Name.Decorator: CODE_KEYWORD,
        Token.Name.Exception: CODE_TEXT,
        Token.Name.Function: CODE_FUNCTION,
        Token.Name.Function.Magic: CODE_FUNCTION,
        Token.Name.Namespace: CODE_TEXT,
        Token.Name.Variable: CODE_TEXT,
        Token.Operator: CODE_TEXT,
        Token.Operator.Word: CODE_KEYWORD,
        Token.Punctuation: CODE_TEXT,
        Token.Whitespace: "",
    }


TABULAFLOW_RICH_SYNTAX_THEME = PygmentsSyntaxTheme(TabulaflowPygmentsStyle)


def _make_code_text_area_theme() -> TextAreaTheme:
    """TextArea theme using the shared TabulaFlow code palette."""
    builtin = TextAreaTheme.get_builtin_theme("dracula")
    assert builtin is not None, "dracula is a built-in theme"
    return TextAreaTheme(
        name="tabulaflow-code",
        base_style=Style(color=CODE_TEXT),
        gutter_style=Style(color="#666666"),
        cursor_style=builtin.cursor_style,
        cursor_line_style=None,
        cursor_line_gutter_style=Style(
            color=(builtin.cursor_line_gutter_style.color if builtin.cursor_line_gutter_style else None),
            bold=True,
        ),
        bracket_matching_style=builtin.bracket_matching_style,
        selection_style=builtin.selection_style,
        syntax_styles={
            "string": Style(color=CODE_STRING),
            "string.documentation": Style(color=CODE_STRING, italic=True),
            "comment": Style(color=CODE_COMMENT),
            "heading.marker": Style(color=CODE_COMMENT),
            "keyword": Style(color=CODE_KEYWORD),
            "repeat": Style(color=CODE_KEYWORD),
            "exception": Style(color=CODE_KEYWORD),
            "include": Style(color=CODE_KEYWORD),
            "keyword.function": Style(color=CODE_KEYWORD),
            "keyword.return": Style(color=CODE_KEYWORD),
            "keyword.operator": Style(color=CODE_KEYWORD),
            "conditional": Style(color=CODE_KEYWORD),
            "number": Style(color=CODE_NUMBER),
            "float": Style(color=CODE_NUMBER),
            "class": Style(color=CODE_TYPE),
            "type": Style(color=CODE_TYPE),
            "type.class": Style(color=CODE_TYPE),
            "type.builtin": Style(color=CODE_TYPE),
            "variable.builtin": Style(color=CODE_TEXT),
            "function": Style(color=CODE_FUNCTION),
            "function.call": Style(color=CODE_FUNCTION),
            "method": Style(color=CODE_FUNCTION),
            "method.call": Style(color=CODE_FUNCTION),
            "boolean": Style(color=CODE_STRING),
            "constant.builtin": Style(color=CODE_STRING),
            "json.null": Style(color=CODE_STRING),
            "regex.punctuation.bracket": Style(color=CODE_TEXT),
            "regex.operator": Style(color=CODE_TEXT),
            "html.end_tag_error": Style(color=CODE_TEXT),
            "tag": Style(color=CODE_KEYWORD),
            "yaml.field": Style(color=CODE_TEXT),
            "json.label": Style(color=CODE_TEXT),
            "toml.type": Style(color=CODE_TYPE),
            "toml.datetime": Style(color=CODE_NUMBER),
            "css.property": Style(color=CODE_TEXT),
            "heading": Style(color=CODE_TEXT),
            "bold": Style(color=CODE_TEXT),
            "italic": Style(color=CODE_TEXT),
            "strikethrough": Style(color=CODE_TEXT),
            "link.label": Style(color=CODE_TEXT),
            "link.uri": Style(color=CODE_TEXT),
            "list.marker": Style(color=CODE_TEXT),
            "inline_code": Style(color=CODE_STRING),
            "punctuation.bracket": Style(color=CODE_TEXT),
            "punctuation.delimiter": Style(color=CODE_TEXT),
            "punctuation.special": Style(color=CODE_TEXT),
            "operator": Style(color=CODE_TEXT),
        },
    )


TABULAFLOW_CODE_TEXT_AREA_THEME = _make_code_text_area_theme()


def configure_code_text_area(text_area: "TextArea") -> None:
    """Apply TabulaFlow code highlighting to a TextArea."""
    text_area.register_theme(TABULAFLOW_CODE_TEXT_AREA_THEME)
    text_area.update_highlight_query("sql", TABULAFLOW_SQL_HIGHLIGHT_QUERY)
    text_area.theme = "tabulaflow-code"
