"""Welcome banner: a seam-free block ``tabulaflow`` wordmark and starter questions.

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

import textwrap
from typing import TYPE_CHECKING

from rich.console import Group
from rich.text import Text

from tabulaflow import __version__
from tabulaflow.app.theme import ACCENT, GITHUB_URL

if TYPE_CHECKING:
    from rich.console import RenderableType

Color = str  # a "#rrggbb" hex color (Rich style token)

# Flat palette, sampled from the original mint -> blue gradient:
COLOR_TABULA: Color = ACCENT  # "#3EB489" mint — the "tabula" letters
COLOR_FLOW: Color = "#48b0ab"  # mint -> blue at 30% — the "flow" letters
# ░ shade for the wordmark's lower half. A dim mint, but red is lifted just enough
# that on a 256-color terminal (e.g. macOS Terminal.app) it quantizes straight to
# neutral grey #303030 instead of a muddy green — no truecolor special-casing.
COLOR_SHADE: Color = "#283629"
# Carve color for the empty halves around the letters. Defaults to the
# ``textual-dark`` background; ``build_banner(surface=...)`` overrides it with the
# widget's own effective background so the carves match the chat log exactly.
COLOR_PAGE: Color = "#121212"

# Hard-wrap example lines at this column so wrapping is identical on every terminal
# width (rather than reflowing at the terminal edge).
_EXAMPLE_WRAP = 70

# Starter questions grouped by category, shown under the banner.
_EXAMPLES: list[tuple[str, list[str]]] = [
    (
        "Large-scale data collection",
        [
            "Find every direct flight from SFO to NYC in the next 10 days",
            "Pull all remote software-engineer jobs posted this week",
            "Collect Hugging Face papers with 20+ upvotes this past month",
        ],
    ),
    (
        "Data enrichment",
        [
            "Tag each review's sentiment and flag any mentioning a refund",
            "Label each failed sample's error pattern as retrieval, reasoning, or output formatting, then visualize the distribution",
            "Extract the vendor, date, and total from each sample expense document",
        ],
    ),
    (
        "Analysis and visualization",
        [
            "Analyze and visualize my monthly spending",
        ],
    ),
]
_TABULA_LETTERS = 6  # "tabula" has 6 letters; the rest ("flow") use COLOR_FLOW

# "tabulaflow" in the half-block "pagga" style (3 rows).
_LOGO_LINES = [
    "░▀█▀░█▀█░█▀█░█░█░█░░░█▀█░█▀▀░█░░░█▀█░█░░░█",
    "░░█░░█▀█░█▀█░█░█░█░░░█▀█░█▀▀░█░░░█░█░█░█░█",
    "░░▀░░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░▀▀▀░▀▀░▀▀",
]

# Each pagga cell -> (top sub-pixel, bottom sub-pixel). 'ink' = a letter stroke,
# 'shade' = the dim ░ block, 'off' = the transparent page. ``▔`` is a sentinel for
# a blackish COLOR_PAGE top half over a COLOR_SHADE bottom half — used under the
# "w" center.
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


def _sub_color(state: str, col: int) -> Color | None:
    """Color for one sub-pixel: a letter color, the shade, or None (transparent)."""
    if state == "ink":
        return COLOR_TABULA if col < _FLOW_START else COLOR_FLOW
    if state == "shade":
        return COLOR_SHADE
    if state == "page":
        return COLOR_PAGE  # explicit blackish block (not the transparent carve)
    return None  # 'off' -> transparent (shows the chat background)


def _cell(top: Color | None, bottom: Color | None, surface: Color) -> tuple[str, str | None]:
    """Return ``(glyph, style)`` for one cell, keeping ink in the seam-free background.

    ``None`` sub-pixels are the empty page. A fully-empty cell renders transparent
    so the chat background shows through; a half-empty cell keeps its colored
    sub-pixel as the (gap-free) background fill and carves the empty half with
    ``surface`` — the chat background color — so it reads as transparent while
    staying seamless.
    """
    if top is None and bottom is None:
        return " ", None  # fully empty -> transparent (chat background)
    if top == bottom:
        return " ", f"on {top}"  # solid letter cell, or a ░ shade block
    if top is not None and bottom is not None:
        return "▀", f"{top} on {bottom}"  # two colors meet (rare)
    if top is not None:  # color top, empty bottom -> color as bg, carve the bottom
        return "▄", f"{surface} on {top}"
    return "▀", f"{surface} on {bottom}"  # empty top, color bottom


def _wordmark(surface: Color) -> list[Text]:
    """Render 'tabulaflow' as three seam-free ``Text`` rows over ``surface``."""
    width = max(len(line) for line in _LOGO_LINES)
    # Decode the art into a 6-row sub-pixel bitmap (None = transparent page).
    bitmap: list[list[Color | None]] = []
    for line in _LOGO_LINES:
        padded = line.ljust(width)
        top: list[Color | None] = []
        bottom: list[Color | None] = []
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
            glyph, style = _cell(top_px, bottom_px, surface)
            row.append(glyph, style=style)
        rows.append(row)
    return rows


def _examples() -> list[Text]:
    """Render the starter-question block: each category as a heading, its example
    questions beneath as bulleted lines, with a blank line between categories.

    Long questions are hard-wrapped at ``_EXAMPLE_WRAP`` with a hanging indent so
    the layout is identical regardless of terminal width.
    """
    rows: list[Text] = []
    for i, (category, questions) in enumerate(_EXAMPLES):
        if i:
            rows.append(Text())  # blank line between categories
        rows.append(Text(category, style="bold dim"))
        for question in questions:
            lines = textwrap.wrap(question, width=_EXAMPLE_WRAP, initial_indent="  • ", subsequent_indent="    ")
            rows.extend(Text(line, style="dim") for line in lines)
    return rows


def build_wordmark(surface: str | None = None) -> RenderableType:
    """Build the 'tabulaflow' wordmark art as a Rich renderable.

    Split from the banner's text block so the art renders in its own widget — the
    half-block art has no meaningful text to select, while the text block does.

    ``surface`` is the chat background color the wordmark's empty halves are carved
    with so they read as transparent — pass the live theme's ``$surface``. Falls
    back to ``COLOR_PAGE`` when not given.
    """
    return Group(*_wordmark(surface or COLOR_PAGE))


def build_banner_text() -> Text:
    """Build the banner's text block — version, project URL, and starter examples.

    Returned as a single ``Text`` (rows joined with newlines) rather than a
    ``Group`` so the widget rendering it is selectable: Textual only extracts
    selection text from widgets whose render is a ``Text``/``Content``.

    """
    # The scheme is dropped from the displayed URL (modern app convention).
    # Rendered as plain text, NOT an OSC-8
    # hyperlink — a real link makes terminals draw a dashed underline affordance
    # that can't be styled away, so we trade clickability for the clean label.
    url_label = GITHUB_URL.split("://", 1)[-1]
    info = Text(f"v{__version__} · {url_label}", style="dim")
    return Text("\n").join([info, Text(), *_examples()])
