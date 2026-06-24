"""Shared HTML page shell for browser dumps (tables and charts).

One document skeleton — sticky banner, base palette, content area, dark
scrollbars — composed by both ``render_table_html`` and ``render_chart_html``
so the two browser pages stay visually consistent. Page-specific assets
(Tabulator / Vega) and body markup are passed in by the caller.
"""

from __future__ import annotations

import html

from tabulaflow.app.theme import ACCENT, ERROR

# Web palette — the single source for the HTML dump colors. ``theme.py`` holds
# the terminal palette (and the mint ``ACCENT`` / ``ERROR`` reused here); these
# are the richer web shades from the design language (page bg, card surface,
# borders). They're also published as the ``:root`` CSS custom properties below,
# so dump.py's table/chart CSS can reference them as ``var(--accent)`` etc.
PAGE_BG = "#0f1117"  # near-black, blue-tinted
CARD_BG = "#1a212c"  # slate panel — lifted clearly off the page so it reads without a border
ROW_STRIPE = "#232b38"  # slate (lifted above the panel)
ROW_HOVER = "#2c3441"  # slate (hover)
BORDER = "#21262d"  # gunmetal gray
TEXT = "#e4e4e7"  # off-white
TEXT_MUTED = "#9aa4b2"  # cool gray
TEXT_DIM = "#6a737d"  # dim gray
POPOVER_BG = "#14171c"  # near-black
POPOVER_BORDER = "#2c3038"  # charcoal gray
SCROLLBAR_TRACK = "#1a1d23"  # near-black
SCROLLBAR_THUMB = "#3a4049"  # slate gray
SCROLLBAR_THUMB_HOVER = "#4a5260"  # gray

_BASE_CSS = f"""
:root {{
    --accent: {ACCENT};
    --bg: {PAGE_BG};
    --card: {CARD_BG};
    --stripe: {ROW_STRIPE};
    --hover: {ROW_HOVER};
    --border: {BORDER};
    --text: {TEXT};
    --text-muted: {TEXT_MUTED};
    --text-dim: {TEXT_DIM};
    --popover-bg: {POPOVER_BG};
    --popover-border: {POPOVER_BORDER};
    --error: {ERROR};
}}
html, body {{ margin: 0; padding: 0; background: {CARD_BG}; color: {TEXT}; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
}}

#content {{
    padding: 20px 24px;
    width: 100%;
    box-sizing: border-box;
}}

/* Dark scrollbars (WebKit/Blink + Firefox). */
* {{ scrollbar-color: {SCROLLBAR_THUMB} {SCROLLBAR_TRACK}; scrollbar-width: thin; }}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {SCROLLBAR_TRACK}; }}
::-webkit-scrollbar-thumb {{ background: {SCROLLBAR_THUMB}; border-radius: 5px;
    border: 2px solid {SCROLLBAR_TRACK}; }}
::-webkit-scrollbar-thumb:hover {{ background: {SCROLLBAR_THUMB_HOVER}; }}
::-webkit-scrollbar-corner {{ background: {SCROLLBAR_TRACK}; }}
"""

def render_page(*, title: str, body: str, head: str = "", scripts: str = "") -> str:
    """Assemble a full HTML document around a page body.

    Args:
        title: Document ``<title>`` (browser tab text); HTML-escaped.
        body: Inner HTML for ``<main id="content">``.
        head: Extra ``<head>`` markup (page-specific ``<style>``/``<script>``
            asset tags), inserted after the base stylesheet.
        scripts: Trailing markup after ``</main>`` (page init ``<script>``s).

    Returns:
        The complete HTML document as a string.
    """
    return (
        "<!doctype html><html><head><meta charset=utf-8>"
        f"<title>{html.escape(title)}</title>"
        f"<style>{_BASE_CSS}</style>"
        f"{head}"
        "</head><body>"
        f'<main id="content">{body}</main>'
        f"{scripts}"
        "</body></html>"
    )
