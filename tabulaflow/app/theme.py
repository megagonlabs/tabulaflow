"""CLI theme constants."""

from __future__ import annotations

from rich.style import Style
from textual.widgets.text_area import TextAreaTheme

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

# Browser visualization colors. Chart specs can override these through
# Vega-Lite; map specs only expose semantic encodings and the output pane owns
# the concrete palette/strokes.
VIZ_CHART_GRID = "#3a4352"
VIZ_CHART_CATEGORY_PALETTE = (
    ACCENT,
    "#5ac8fa",
    "#f5a623",
    "#bd6cf0",
    "#f06292",
    "#4dd0e1",
    "#aed581",
    "#ff8a65",
)

VIZ_MAP_DEFAULT_COLOR = "#4285f4"
VIZ_MAP_ROUTE_COLOR = "#1558d6"
VIZ_MAP_CATEGORY_PALETTE = (
    VIZ_MAP_DEFAULT_COLOR,
    "#ea4335",
    "#fbbc04",
    "#34a853",
    "#a142f4",
    "#fbbc54",
    "#46bdc6",
    "#7cb342",
)
VIZ_MAP_PIN_DEFAULT_COLOR = "#ea4335"
VIZ_MAP_PIN_TOP = "#ff6f61"
VIZ_MAP_PIN_BOTTOM = "#d93025"
VIZ_MAP_PIN_OUTLINE = "#a52714"
VIZ_MAP_PIN_HOLE = "#f8fafc"
VIZ_MAP_PIN_INNER = "#fff4f2"


def _make_transparent_dracula() -> TextAreaTheme:
    """Dracula TextArea theme with backgrounds removed so CSS $surface shows through."""
    builtin = TextAreaTheme.get_builtin_theme("dracula")
    assert builtin is not None, "dracula is a built-in theme"
    return TextAreaTheme(
        name="dracula-transparent",
        base_style=Style(color=builtin.base_style.color if builtin.base_style else None),
        gutter_style=Style(color="#666666"),
        cursor_style=builtin.cursor_style,
        cursor_line_style=None,
        cursor_line_gutter_style=Style(
            color=(builtin.cursor_line_gutter_style.color if builtin.cursor_line_gutter_style else None),
            bold=True,
        ),
        bracket_matching_style=builtin.bracket_matching_style,
        selection_style=builtin.selection_style,
        syntax_styles=dict(builtin.syntax_styles),
    )


DRACULA_TRANSPARENT = _make_transparent_dracula()
