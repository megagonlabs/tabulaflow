"""CLI theme constants."""

from __future__ import annotations

from rich.style import Style
from textual.widgets.text_area import TextAreaTheme

ACCENT = "#3EB489"
ACCENT_BOLD = f"bold {ACCENT}"
ACCENT_RGB = (62, 180, 137)

# Dim mint — used for inactive/unfocused states of widgets that normally
# display mint accents (e.g. focused-vs-unfocused AgentResultWidget). Same
# hue as ACCENT, lower saturation/lightness — modern app pattern (Linear,
# VS Code) for "this is the same family, but inactive." Chosen to work in
# both roles: as a fill color (black text on this bg ≈ 5:1 contrast) and
# as a text color (this on dark bg ≈ 5:1 contrast).
ACCENT_DIM = "#67857b"

# Color used for keyboard-key glyphs in hint bars (e.g. "Esc", "Enter", "[/]").
# Kept separate from ACCENT so the two can evolve independently.
KEY_HINT_COLOR = "#9EC8B2"
KEY_HINT = f"bold {KEY_HINT_COLOR}"
# Dim version is just the bold-prefixed ACCENT_DIM — one mint dim color
# serves both the accent role (e.g. record pill bg) and the key-hint role.
KEY_HINT_DIM = f"bold {ACCENT_DIM}"


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
