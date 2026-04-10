"""CLI theme constants."""

from __future__ import annotations

from rich.style import Style
from textual.widgets.text_area import TextAreaTheme

ACCENT = "#3EB489"
ACCENT_BOLD = f"bold {ACCENT}"
ACCENT_RGB = (62, 180, 137)
ACCENT_DIM_RGB = (100, 160, 130)


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
