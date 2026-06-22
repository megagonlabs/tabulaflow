"""Shared HTML page shell for browser dumps (tables and charts).

One document skeleton — sticky banner, base palette, content area, dark
scrollbars — composed by both ``render_table_html`` and ``render_chart_html``
so the two browser pages stay visually consistent. Page-specific assets
(Tabulator / Vega) and body markup are passed in by the caller.
"""

from __future__ import annotations

import html

from tabulaflow.app.theme import ACCENT, ERROR, GITHUB_SLUG, GITHUB_URL

# Web palette — the single source for the HTML dump colors. ``theme.py`` holds
# the terminal palette (and the mint ``ACCENT`` / ``ERROR`` reused here); these
# are the richer web shades from the design language (page bg, card surface,
# borders). They're also published as the ``:root`` CSS custom properties below,
# so dump.py's table/chart CSS can reference them as ``var(--accent)`` etc.
PAGE_BG = "#0f1117"  # near-black, blue-tinted
CARD_BG = "#131720"  # dark slate
ROW_STRIPE = "#1a1f2a"  # slate (lifted)
ROW_HOVER = "#1f2532"  # slate (hover)
BORDER = "#21262d"  # gunmetal gray
TEXT = "#e4e4e7"  # off-white
TEXT_MUTED = "#9aa4b2"  # cool gray
TEXT_DIM = "#6a737d"  # dim gray
POPOVER_BG = "#14171c"  # near-black
POPOVER_BORDER = "#2c3038"  # charcoal gray

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
html, body {{ margin: 0; padding: 0; min-height: 100%; background: {PAGE_BG}; color: {TEXT}; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
}}

#banner {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    border-bottom: 1px solid {BORDER};
    background: {PAGE_BG};
    position: sticky;
    top: 0;
    z-index: 50;
}}
#logo {{
    color: {ACCENT};
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.05em;
    user-select: none;
}}
#repo {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #8a94a3;
    text-decoration: none;
    font-size: 13px;
    padding: 4px 10px;
    border-radius: 4px;
}}
#repo:hover {{ background: #1f242c; color: #e6e6e6; }}
#repo svg {{ width: 16px; height: 16px; fill: currentColor; }}

#content {{
    padding: 20px 24px;
    width: 100%;
    box-sizing: border-box;
}}

/* Dark scrollbars (WebKit/Blink + Firefox). */
* {{ scrollbar-color: #3a4049 #1a1d23; scrollbar-width: thin; }}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: #1a1d23; }}
::-webkit-scrollbar-thumb {{ background: #3a4049; border-radius: 5px;
    border: 2px solid #1a1d23; }}
::-webkit-scrollbar-thumb:hover {{ background: #4a5260; }}
::-webkit-scrollbar-corner {{ background: #1a1d23; }}
"""

# GitHub mark, rendered in the banner's repo link.
_GITHUB_SVG = (
    '<svg viewBox="0 0 16 16" aria-hidden="true">'
    '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38'
    " 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53"
    " .63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95"
    " 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68"
    " 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15"
    " 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2"
    ' 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>'
)


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
        '<header id="banner">'
        '<span id="logo">tabulaflow</span>'
        f'<a id="repo" href="{GITHUB_URL}" target="_blank" rel="noopener">{_GITHUB_SVG}{GITHUB_SLUG}</a>'
        "</header>"
        f'<main id="content">{body}</main>'
        f"{scripts}"
        "</body></html>"
    )
