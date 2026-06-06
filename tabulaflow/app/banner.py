"""Welcome banner: the gradient ``tabulaflow`` wordmark + sine flow wave."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from rich.console import Group
from rich.text import Text

from tabulaflow.app.theme import ACCENT_DIM, ACCENT_RGB

if TYPE_CHECKING:
    from rich.console import RenderableType


# "tabulaflow" wordmark in the half-block "pagga" style (3 rows), paired with a
# small sine "flow" wave to its right. The wordmark traverses the first
# ``_LOGO_LETTERS_FRACTION`` of a mint -> blue gradient and the wave traverses
# the rest, so the color change reads clearly on both.
_LOGO_LINES = [
    "░▀█▀░█▀█░█▀▄░█░█░█░░░█▀█░█▀▀░█░░░█▀█░█░█",
    "░░█░░█▀█░█▀▄░█░█░█░░░█▀█░█▀▀░█░░░█░█░█▄█",
    "░░▀░░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░▀▀▀░▀░▀",
]
_TAGLINE = "AI that outputs tables"

_LOGO_MINT = ACCENT_RGB  # (62, 180, 137)
_LOGO_BLUE = (96, 165, 250)
_LOGO_LETTERS_FRACTION = 0.3  # share of the mint -> blue sweep spent on the wordmark
_LOGO_GAP = 2  # blank columns between the wordmark and the wave

# Sine "water" wave settings.
_WAVE_WIDTH = 17  # columns of wave
_WAVE_ROWS = 2
_WAVE_EIGHTHS = " ▁▂▃▄▅▆▇█"  # vertical eighth blocks, fill from the bottom up
_WAVE_SUBPIX = _WAVE_ROWS * 8
_WAVE_FLOOR = 0.08  # thin sliver of water at the trough so the wave reads continuous
_WAVE_PHASE_INSET = 0.5  # trim the sine domain to [inset, 2pi - inset]


def _wave_levels(width: int) -> list[float]:
    """Fill level (floor .. 1=full) per column across the trimmed sine domain."""
    lo = _WAVE_PHASE_INSET
    hi = 2 * math.pi - _WAVE_PHASE_INSET
    levels = []
    for i in range(width):
        angle = lo + i / max(width - 1, 1) * (hi - lo)
        levels.append(_WAVE_FLOOR + (1 - _WAVE_FLOOR) * (math.sin(angle) + 1) / 2)
    return levels


def _wave_rows(width: int = _WAVE_WIDTH) -> list[str]:
    """Render the sine 'water' wave as ``_WAVE_ROWS`` eighth-block text lines."""
    levels = _wave_levels(width)
    rows = []
    for cell in range(_WAVE_ROWS - 1, -1, -1):  # top cell first
        line = ""
        for level in levels:
            filled = level * _WAVE_SUBPIX - cell * 8  # sub-pixels filled within this cell
            line += _WAVE_EIGHTHS[max(0, min(8, round(filled)))]
        rows.append(line)
    return rows


def _logo_gradient_block(lines: list[str], start: tuple[int, int, int], end: tuple[int, int, int]) -> list[Text]:
    """Color each line of a block with a left-to-right ``start`` -> ``end`` gradient."""
    cols = max(len(line) for line in lines)
    out = []
    for line in lines:
        text = Text()
        for ci, ch in enumerate(line):
            t = ci / max(cols - 1, 1)
            r, g, b = (round(start[i] + (end[i] - start[i]) * t) for i in range(3))
            text.append(ch, style=f"bold #{r:02x}{g:02x}{b:02x}")
        out.append(text)
    return out


def _build_logo() -> Text:
    """Wordmark + flow wave splitting one mint -> blue gradient."""
    wave = _wave_rows()
    # The wave is shorter than the wordmark; pad blank rows on top so the water
    # stays bottom-aligned with the wordmark's baseline.
    wave = [" " * _WAVE_WIDTH] * (len(_LOGO_LINES) - len(wave)) + wave

    pagga_w = max(len(line) for line in _LOGO_LINES)

    def _lerp(i: int) -> int:
        return round(_LOGO_MINT[i] + (_LOGO_BLUE[i] - _LOGO_MINT[i]) * _LOGO_LETTERS_FRACTION)

    split: tuple[int, int, int] = (_lerp(0), _lerp(1), _lerp(2))

    left = _logo_gradient_block([line.ljust(pagga_w) for line in _LOGO_LINES], _LOGO_MINT, split)
    right = _logo_gradient_block(wave, split, _LOGO_BLUE)  # remaining stretch of the sweep

    out: list[Text] = []
    for left_line, right_line in zip(left, right):
        line = Text()
        line.append_text(left_line)
        line.append(" " * _LOGO_GAP)
        line.append_text(right_line)
        out.append(line)
    return Text("\n").join(out)


def build_banner(*, model: str) -> RenderableType:
    """Build the welcome banner as a Rich renderable."""
    info = Text.from_markup(
        f"[dim]model:[/dim] {model}    [dim]Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to exit[/dim]"
    )
    return Group(
        _build_logo(),
        Text(_TAGLINE, style=f"italic {ACCENT_DIM}"),
        Text(),
        info,
    )
