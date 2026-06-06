"""Preview the pagga wordmark banner with a flow/wave sparkline on the right.

The "tabulaflow" wordmark is hardcoded in the half-block "pagga" style (no
figlet/pyfiglet dependency) and a sparkline-style "flow" wave is appended to its
right. The whole thing gets a left-to-right mint -> violet gradient and is
wrapped in the real TUI welcome card. A few wave styles are shown for comparison.

Run with::

    uv run scripts/preview_banners.py
    uv run scripts/preview_banners.py | less -R   # keep colors
"""

from __future__ import annotations

import math

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from tabulaflow.app.theme import ACCENT_DIM, ACCENT_RGB

MODEL = "openai-responses:gpt-5"
TAGLINE = "AI that outputs tables"

# "tabulaflow" in the half-block "pagga" style (39 cols, 3 rows).
PAGGA = [
    "░▀█▀░█▀█░█▀▄░█░█░█░░░█▀█░█▀▀░█░░░█▀█░█░█",
    "░░█░░█▀█░█▀▄░█░█░█░░░█▀█░█▀▀░█░░░█░█░█▄█",
    "░░▀░░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░▀▀▀░▀░▀",
]

MINT = ACCENT_RGB  # (62, 180, 137)
BLUE = (96, 165, 250)  # same blue as the earlier mint -> blue gradient

GAP = 2  # blank columns between the wordmark and the wave
WAVE_WIDTH = 17  # columns of wave (wider = gentler slopes; keep total <= ~71)
LETTERS_FRACTION = 0.3  # share of the mint->blue sweep spent on the wordmark

_ROWS = 2
# Vertical eighth blocks (fill from the bottom up). Index 0..8.
_EIGHTHS = " ▁▂▃▄▅▆▇█"
_SUBPIX = _ROWS * 8  # vertical sub-pixels -> fine-grained, smooth surface


# Keep a thin sliver of water at the trough so the wave reads as continuous
# (a level of 0 renders an empty cell, which looks like a break).
_WAVE_FLOOR = 0.08

# Trim the sine domain to [inset, 2pi - inset] so the wave starts/ends a little
# past the zero crossings (raise for a flatter, more centered swell).
_WAVE_PHASE_INSET = 0.5


def _sine_levels(width: int) -> list[float]:
    """Fill level (floor .. 1=full) per column across the trimmed sine domain."""
    lo = _WAVE_PHASE_INSET
    hi = 2 * math.pi - _WAVE_PHASE_INSET
    levels = []
    for i in range(width):
        angle = lo + i / max(width - 1, 1) * (hi - lo)
        levels.append(_WAVE_FLOOR + (1 - _WAVE_FLOOR) * (math.sin(angle) + 1) / 2)
    return levels


def wave_water(width: int = WAVE_WIDTH) -> list[str]:
    """Filled 'water' wave following one sine cycle, at eighth-block resolution.

    Water fills each column from the bottom up to its surface level, so the only
    partial cell is the one at the surface -- rendered with an eighth block for
    smooth, fine-grained steps.
    """
    levels = _sine_levels(width)
    rows = []
    for cell in range(_ROWS - 1, -1, -1):  # top cell first
        line = ""
        for level in levels:
            filled = level * _SUBPIX - cell * 8  # sub-pixels filled within this cell
            line += _EIGHTHS[max(0, min(8, round(filled)))]
        rows.append(line)
    return rows


def gradient_block(
    lines: list[str], start: tuple[int, int, int], end: tuple[int, int, int]
) -> list[Text]:
    """Color each line of a block with a left-to-right ``start`` -> ``end`` gradient.

    The gradient spans the block's own width, so two blocks colored separately
    each get a full sweep (independent of one another).
    """
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


def build_logo(gap: int = GAP) -> Text:
    """Wordmark + flow wave splitting one mint -> blue gradient.

    The wordmark traverses the first ``LETTERS_FRACTION`` of the gradient and the
    wave traverses the rest, each across its own width, so the color change reads
    clearly on both.
    """
    wave = wave_water()
    # The wave is shorter than the wordmark; pad blank rows on top so the water
    # stays bottom-aligned with the wordmark's baseline.
    wave = [" " * WAVE_WIDTH] * (len(PAGGA) - len(wave)) + wave

    pagga_w = max(len(p) for p in PAGGA)
    split = tuple(
        round(MINT[i] + (BLUE[i] - MINT[i]) * LETTERS_FRACTION) for i in range(3)
    )

    left = gradient_block([p.ljust(pagga_w) for p in PAGGA], MINT, split)
    right = gradient_block(wave, split, BLUE)  # remaining stretch of the sweep

    out = []
    for l, r in zip(left, right):
        line = Text()
        line.append_text(l)
        line.append(" " * gap)
        line.append_text(r)
        out.append(line)
    return Text("\n").join(out)


def welcome_card(logo: Text) -> Panel:
    """Wrap a colored logo in the TUI welcome card (logo + tagline + info)."""
    info = Text.from_markup(
        f"[dim]model:[/dim] {MODEL}    "
        "[dim]Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to exit[/dim]"
    )
    border = f"#{MINT[0]:02x}{MINT[1]:02x}{MINT[2]:02x}"
    body = Group(logo, Text(TAGLINE, style=f"italic {ACCENT_DIM}"), Text(), info)
    return Panel.fit(body, border_style=border, padding=(1, 3))


def main() -> None:
    console = Console()
    console.print(Rule("[bold yellow]continuous mint->blue (left to right)[/]"))
    console.print(welcome_card(build_logo()))
    console.print()


if __name__ == "__main__":
    main()
