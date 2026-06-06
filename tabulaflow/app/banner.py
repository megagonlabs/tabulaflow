"""Welcome banner: the gradient ``tabulaflow`` wordmark + sine flow wave."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from rich.console import Group
from rich.text import Text

from tabulaflow.app.theme import ACCENT_RGB

if TYPE_CHECKING:
    from rich.console import RenderableType


# "tabulaflow" wordmark in the half-block "pagga" style (3 rows), paired with a
# small sine "flow" wave to its right. The wordmark traverses the first
# ``_LOGO_LETTERS_FRACTION`` of a mint -> blue gradient and the wave traverses
# the rest, so the color change reads clearly on both.
_LOGO_LINES = [
    "░▀█▀░█▀█░█▀█░█░█░█░░░█▀█░█▀▀░█░░░█▀█░█░█",
    "░░█░░█▀█░█▀█░█░█░█░░░█▀█░█▀▀░█░░░█░█░█▄█",
    "░░▀░░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░▀▀▀░▀░▀",
]
_TAGLINE = "AI that outputs tables"

_LOGO_MINT = ACCENT_RGB  # (62, 180, 137)
_LOGO_BLUE = (96, 165, 250)
_LOGO_LETTERS_FRACTION = 0.3  # share of the mint -> blue sweep spent on the wordmark
_LOGO_GAP = 2  # blank columns between the wordmark and the wave

# Background "shade": ``░`` reads as a stipple and renders badly in iTerm2, so we
# draw a solid full block dimmed to ``_LOGO_SHADE_DIM`` of the stroke brightness
# in its place. Letter strokes get no background, so the empty half of each
# half-block stays transparent against the page.
_LOGO_SHADE_CHAR = "░"
_LOGO_SHADE_DIM = 0.3  # shade-block brightness vs the bright letter strokes (0=black, 1=same)

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


def _logo_gradient_block(
    lines: list[str],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    weight: str = "bold",
    shade: bool = False,
) -> list[Text]:
    """Color each line of a block with a left-to-right ``start`` -> ``end`` gradient.

    When ``shade`` is set, ``_LOGO_SHADE_CHAR`` cells become a solid full block
    painted at ``_LOGO_SHADE_DIM`` of the local gradient color — a clean,
    iTerm-safe stand-in for a shade glyph. The letter strokes keep no background,
    so the empty half of each half-block stays transparent (page background).
    """
    cols = max(len(line) for line in lines)
    out = []
    for line in lines:
        text = Text()
        for ci, ch in enumerate(line):
            t = ci / max(cols - 1, 1)
            r, g, b = (round(start[i] + (end[i] - start[i]) * t) for i in range(3))
            if shade and ch == _LOGO_SHADE_CHAR:  # solid dim block in place of the shade glyph
                r, g, b = (round(c * _LOGO_SHADE_DIM) for c in (r, g, b))
                ch = "█"
            text.append(ch, style=f"{weight} #{r:02x}{g:02x}{b:02x}")
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

    left = _logo_gradient_block([line.ljust(pagga_w) for line in _LOGO_LINES], _LOGO_MINT, split, shade=True)
    right = _logo_gradient_block(wave, split, _LOGO_BLUE)  # remaining stretch of the sweep

    out: list[Text] = []
    for left_line, right_line in zip(left, right):
        line = Text()
        line.append_text(left_line)
        line.append(" " * _LOGO_GAP)
        line.append_text(right_line)
        out.append(line)
    return Text("\n").join(out)


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
    # Tagline sweeps the same mint -> split stretch as the wordmark (first
    # _LOGO_LETTERS_FRACTION of the mint -> blue gradient).
    split: tuple[int, int, int] = tuple(  # type: ignore[assignment]
        round(_LOGO_MINT[i] + (_LOGO_BLUE[i] - _LOGO_MINT[i]) * _LOGO_LETTERS_FRACTION) for i in range(3)
    )
    tagline = _logo_gradient_block([_TAGLINE], _LOGO_MINT, split, weight="italic")[0]
    return Group(
        _build_logo(),
        tagline,
        Text(),
        info,
    )
