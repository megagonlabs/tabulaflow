"""Welcome banner: a seam-free block ``tabulaflow`` wordmark, tagline, and info line.

The wordmark is the half-block "pagga" art, but rendered so it stays seamless in
macOS Terminal.app — whose renderer leaves a hairline between vertically-stacked
*foreground* block glyphs (``█ ▀ ▄``), which shows up as scanlines through the
letters. The fix, borrowed from terminal image viewers (chafa/viu/timg):

  * Decode the 3-row art into a 6-px-tall sub-pixel bitmap (each cell is two
    vertical sub-pixels).
  * Draw each cell so the *ink* sub-pixel is always a cell **background fill**
    (background fills tile gap-free across rows) and only the empty side is a
    foreground half-block. Every ink-to-ink connection is then seam-free.

Colors are four flat tones sampled from the old mint -> blue gradient. Flat (not
interpolated) colors have nothing to band, so the banner also looks identical on
256-color terminals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group
from rich.text import Text

from tabulaflow.app.theme import ACCENT

if TYPE_CHECKING:
    from rich.console import RenderableType

Color = str  # a "#rrggbb" hex color (Rich style token)

# Flat palette, sampled from the original mint -> blue gradient:
COLOR_TABULA: Color = ACCENT  # "#3EB489" mint — the "tabula" letters
COLOR_FLOW: Color = "#48b0ab"  # mint -> blue at 30% — the "flow" letters
COLOR_SHADE: Color = "#133629"  # mint dimmed to 30% — the ░ shade blocks
COLOR_PAGE: Color = "#0f1117"  # black-ish page below/around the letters

_TAGLINE = "AI for everything tabular"
_TABULA_LETTERS = 6  # "tabula" has 6 letters; the rest ("flow") use COLOR_FLOW

# "tabulaflow" in the half-block "pagga" style (3 rows).
_LOGO_LINES = [
    "░▀█▀░█▀█░█▀█░█░█░█░░░█▀█░█▀▀░█░░░█▀█░█░█",
    "░░█░░█▀█░█▀█░█░█░█░░░█▀█░█▀▀░█░░░█░█░█▀█",
    "░░▀░░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░▀▀▀░▀░▀",
]

# Each pagga cell -> (top sub-pixel, bottom sub-pixel). 'ink' = a letter stroke,
# 'shade' = the dim ░ block, 'off' = the black-ish page.
_DECODE = {
    "█": ("ink", "ink"),
    "▀": ("ink", "off"),
    "▄": ("off", "ink"),
    "░": ("shade", "shade"),
    " ": ("off", "off"),
}


def _flow_start_col(lines: list[str]) -> int:
    """Column where the first 'flow' letter begins (splits tabula | flow)."""
    width = max(len(line) for line in lines)
    grid = [line.ljust(width) for line in lines]
    is_gap = [all(grid[r][c] in "░ " for r in range(len(grid))) for c in range(width)]
    groups: list[int] = []  # start column of each letter group
    in_letter = False
    for c in range(width):
        if not is_gap[c] and not in_letter:
            groups.append(c)
            in_letter = True
        elif is_gap[c]:
            in_letter = False
    return groups[_TABULA_LETTERS] if len(groups) > _TABULA_LETTERS else width


_FLOW_START = _flow_start_col(_LOGO_LINES)


def _is_ink(c: Color) -> bool:
    return c in (COLOR_TABULA, COLOR_FLOW)


def _sub_color(state: str, col: int) -> Color:
    """Flat color for one sub-pixel: page, shade, or the tabula/flow letter color."""
    if state == "ink":
        return COLOR_TABULA if col < _FLOW_START else COLOR_FLOW
    if state == "shade":
        return COLOR_SHADE
    return COLOR_PAGE


def _cell(top: Color, bottom: Color) -> tuple[str, str | None]:
    """Return ``(glyph, style)`` for one cell, keeping ink in the seam-free background.

    A hairline gap at a cell edge reveals the cell's *background*, so the ink
    sub-pixel is always the background fill and the empty side is carved with a
    foreground half-block.
    """
    if top == bottom:
        if top == COLOR_PAGE:
            return " ", None  # fully empty -> transparent
        return " ", f"on {top}"  # solid letter cell, or a ░ shade block
    if _is_ink(top):  # ink on top -> ink as background, carve the bottom
        return "▄", f"{bottom} on {top}"
    if _is_ink(bottom):  # ink on bottom -> ink as background, carve the top
        return "▀", f"{top} on {bottom}"
    return "▀", f"{top} on {bottom}"  # two backgrounds meet (rare)


def _wordmark() -> list[Text]:
    """Render 'tabulaflow' as three seam-free ``Text`` rows."""
    width = max(len(line) for line in _LOGO_LINES)
    # Decode the art into a 6-row sub-pixel bitmap of flat colors.
    bitmap: list[list[Color]] = []
    for line in _LOGO_LINES:
        padded = line.ljust(width)
        top: list[Color] = []
        bottom: list[Color] = []
        for col, ch in enumerate(padded):
            top_state, bottom_state = _DECODE.get(ch, ("off", "off"))
            top.append(_sub_color(top_state, col))
            bottom.append(_sub_color(bottom_state, col))
        bitmap.append(top)
        bitmap.append(bottom)

    rows: list[Text] = []
    for tr in range(len(_LOGO_LINES)):
        row = Text()
        for top_px, bottom_px in zip(bitmap[2 * tr], bitmap[2 * tr + 1]):
            glyph, style = _cell(top_px, bottom_px)
            row.append(glyph, style=style)
        rows.append(row)
    return rows


# Provider prefixes -> human-friendly vendor names for the banner.
_PROVIDER_NAMES = {
    "openai-responses": "OpenAI",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google-vertex": "Google",
    "google": "Google",
    "fireworks": "Fireworks",
    "together": "Together",
}
# Model-name tokens shown as an uppercase acronym rather than title-cased.
_MODEL_ACRONYMS = {"gpt"}


def _pretty_model(model: str) -> str:
    """Humanize a model id, e.g. ``openai-responses:gpt-5.4`` -> ``OpenAI GPT 5.4``."""
    provider, sep, name = model.partition(":")
    if not sep:  # no provider prefix
        provider, name = "", provider
    provider_label = _PROVIDER_NAMES.get(provider, provider.replace("-", " ").title())

    parts = []
    for tok in name.split("-"):
        if tok.lower() in _MODEL_ACRONYMS:
            parts.append(tok.upper())
        elif tok[:1].isalpha():
            parts.append(tok.capitalize())
        else:  # version numbers like 5.4, 2.0
            parts.append(tok)
    return " ".join([provider_label, *parts]).strip()


def build_banner(*, model: str) -> RenderableType:
    """Build the welcome banner as a Rich renderable."""
    info = Text.from_markup(
        f"[dim]{_pretty_model(model)}[/dim]      "
        "[dim]Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to exit[/dim]"
    )
    return Group(
        *_wordmark(),
        Text(_TAGLINE, style=f"italic {COLOR_TABULA}"),
        Text(),
        info,
    )
