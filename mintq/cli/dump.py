"""Helpers for dumping cell values and result tables to disk for browser viewing.

Provides:
- ``sniff_binary``: magic-byte content sniffer for common media MIMEs.
- ``try_decode_base64``: tolerant base64 decoder for plain and data-URI strings.
- ``serialize_cell``: pick (content, file-suffix) for a single cell value.
- ``write_cell_dump``: write a serialized cell into the dumps directory.
- ``render_table_html``: render a DataFrame to HTML with inline media renderers
  for image/audio/video/PDF columns, spilling large blobs to sibling files.
"""

from __future__ import annotations

import ast
import base64
import binascii
import html
import json
import re
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


# ---------------------------------------------------------------------------
# Magic-byte sniffing
# ---------------------------------------------------------------------------


def sniff_binary(raw: bytes) -> tuple[str, str] | None:
    """Return ``(suffix, mime)`` for recognized media signatures, else ``None``.

    Covers common image/audio/video/document formats observed in DB BLOB
    columns. Suffix includes the leading dot so callers can append it to
    file names directly.
    """
    if len(raw) < 4:
        return None
    head = bytes(raw[:16])
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return ".wav", "audio/wav"
    if head.startswith(b"BM"):
        return ".bmp", "image/bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tif", "image/tiff"
    if head.startswith(b"%PDF-"):
        return ".pdf", "application/pdf"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3", "audio/mpeg"
    if head.startswith(b"OggS"):
        return ".ogg", "audio/ogg"
    if head.startswith(b"fLaC"):
        return ".flac", "audio/flac"
    if head[4:8] == b"ftyp":
        return ".mp4", "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm", "video/webm"
    # SVG is text-mode XML; peek at a slightly longer window
    head_lower = raw[:256].lstrip().lower()
    if head_lower.startswith(b"<svg") or (head_lower.startswith(b"<?xml") and b"<svg" in head_lower):
        return ".svg", "image/svg+xml"
    return None


# ---------------------------------------------------------------------------
# Base64 detection
# ---------------------------------------------------------------------------

_DATA_URI_RE = re.compile(r"^data:(?P<mime>[^;,]+)?(?:;[^,]*)*,(?P<payload>.*)$", re.DOTALL)
_BASE64_CHARS_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$")
_BASE64_MIN_LEN = 64


def try_decode_base64(s: str) -> bytes | None:
    """Try to decode ``s`` as base64 (plain or ``data:...;base64,...`` URI).

    Returns the decoded bytes, or ``None`` if the input doesn't look like
    base64 or is shorter than ``_BASE64_MIN_LEN`` (guards against false
    positives on short strings that happen to be base64-alphabet).
    """
    if len(s) < _BASE64_MIN_LEN:
        return None
    payload = s.strip()
    m = _DATA_URI_RE.match(payload)
    if m:
        payload = m.group("payload")
    if not _BASE64_CHARS_RE.match(payload):
        return None
    try:
        return base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError):
        return None


# ---------------------------------------------------------------------------
# Cell serialization
# ---------------------------------------------------------------------------

_SQL_RE = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|EXPLAIN)\b",
    re.IGNORECASE,
)
_PY_RE = re.compile(r"^\s*(def |class |import |from |if __name__)")


def serialize_cell(value: object) -> tuple[str | bytes, str]:
    """Return ``(content, suffix)`` for writing ``value`` at full fidelity.

    Binary inputs (``bytes``/``bytearray``/``memoryview``) get sniffed for
    a known media extension. String inputs that decode as base64 of a
    recognized media format are returned as the decoded bytes with that
    extension — covers DB columns that store images as base64 text.
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        sniffed = sniff_binary(raw)
        return raw, sniffed[0] if sniffed else ".bin"

    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False, default=str), ".json"

    if isinstance(value, str):
        decoded = try_decode_base64(value)
        if decoded is not None:
            sniffed = sniff_binary(decoded)
            if sniffed:
                return decoded, sniffed[0]
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(value)
            except Exception:
                continue
            if isinstance(parsed, (dict, list)):
                return (
                    json.dumps(parsed, indent=2, ensure_ascii=False, default=str),
                    ".json",
                )
        if _SQL_RE.match(value):
            return value, ".sql"
        if _PY_RE.match(value):
            return value, ".py"
        return value, ".txt"

    return str(value), ".txt"


def write_cell_dump(value: object, dumps_dir: Path) -> Path:
    """Serialize ``value`` and write it into ``dumps_dir``; return the path.

    File name is ``C_<6 hex>{suffix}``. Caller is responsible for
    deciding whether to reuse an existing dump.
    """
    content, suffix = serialize_cell(value)
    path = dumps_dir / f"C_{secrets.token_hex(3)}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (bytes, bytearray)):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Table HTML rendering with inline media
# ---------------------------------------------------------------------------


def _extract_blob(value: object) -> bytes | None:
    """Coerce a cell value into bytes if possible.

    Handles four cases:
      - Raw ``bytes``/``bytearray``/``memoryview``
      - HuggingFace ``Image``/``Audio`` struct: ``{"bytes": <data>, "path": ...}``
        (how DuckDB returns ``STRUCT(bytes BLOB, path VARCHAR)`` columns from
        cached HF parquet)
      - ``str`` that decodes as base64 (plain or data-URI)
    Returns ``None`` if no recognizable blob is present.
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, dict):
        inner = value.get("bytes")
        if isinstance(inner, (bytes, bytearray, memoryview)):
            return bytes(inner)
    if isinstance(value, str):
        return try_decode_base64(value)
    return None


def _sniff_column(series: "pd.Series", *, sample_n: int = 5, threshold: float = 0.6) -> tuple[str, str] | None:
    """Vote on a column's MIME type from its first ``sample_n`` non-null values.

    Returns the winning ``(suffix, mime)`` if at least ``threshold`` of the
    sample agrees, else ``None``. Avoids misclassifying mixed-type columns.
    """
    sample = series.dropna().head(sample_n)
    if sample.empty:
        return None
    votes: dict[tuple[str, str], int] = {}
    for val in sample:
        blob = _extract_blob(val)
        if blob is None:
            continue
        sniffed = sniff_binary(blob)
        if sniffed is not None:
            votes[sniffed] = votes.get(sniffed, 0) + 1
    if not votes:
        return None
    winner, count = max(votes.items(), key=lambda kv: kv[1])
    if count / len(sample) >= threshold:
        return winner
    return None


_FILE_ICON_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<polyline points="14 2 14 8 20 8"/></svg>'
)


def _fmt_size(n: int) -> str:
    """Human-readable byte size (B / KB / MB)."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _file_link(src: str, label: str, size: int, *, new_tab: bool) -> str:
    """Render a file anchor with icon + label + dim size annotation."""
    target = ' target="_blank" rel="noopener"' if new_tab else ""
    return (
        f'<a class="file-link" href="{src}"{target}>'
        f"{_FILE_ICON_SVG}<span>{label}</span>"
        f'<span class="file-size">{_fmt_size(size)}</span></a>'
    )


def _render_blob(src: str, mime: str, size: int) -> str:
    """Render a blob reference as inline media markup.

    ``src`` is either a ``data:`` URI (inline) or a relative file URL
    (spilled to sibling file). Same markup either way; only the src
    differs. Image cells size themselves via CSS caps; the page wires
    a single ``window.load`` → ``table.redraw(true)`` so Tabulator
    re-measures columns after images have decoded.
    """
    if mime.startswith("image/"):
        # Eager load (no ``loading="lazy"``). Lazy images don't block the
        # ``window.load`` event (per HTML spec), so the post-load
        # ``table.redraw(true)`` would race them and measure columns
        # against undecoded 0×0 cells. Tabulator's virtual scroll already
        # only renders visible rows, so off-screen optimization isn't
        # needed and the race isn't worth the marginal benefit.
        return f'<img src="{src}">'
    if mime.startswith("audio/"):
        return f'<audio controls preload="none" src="{src}"></audio>'
    if mime.startswith("video/"):
        return f'<video controls preload="none" src="{src}"></video>'
    if mime == "application/pdf":
        return _file_link(src, "PDF", size, new_tab=True)
    return _file_link(src, "binary", size, new_tab=False)


def _safe_col_name(name: str) -> str:
    """Sanitize a column name for use in a file path."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:32] or "col"


_DEFAULT_MAX_ROWS = 50_000
_DEFAULT_INLINE_CAP = 256 * 1024  # 256 KB
# Cap on the full text stored per non-media cell (sent to Tabulator's data
# array). Truncated text above this is replaced with a head excerpt + note;
# users can press `b` on the source row/cell for full content.
_CELL_TEXT_HARD_CAP = 1024 * 1024
# Display truncation in the cell view (full value still in row data; modal
# shows full).
_CELL_DISPLAY_CAP = 120


def _load_tabulator_assets() -> tuple[str, str]:
    """Load Tabulator JS + CSS from package resources.

    Returns ``(js_source, css_source)``. The files are vendored under
    ``mintq/cli/assets/tabulator/`` and read once per call (callers
    typically invoke this once per ``render_table_html``, which is fine
    given the file sizes).
    """
    from importlib.resources import files

    base = files("mintq.cli.assets.tabulator")
    js = base.joinpath("tabulator.min.js").read_text(encoding="utf-8")
    css = base.joinpath("tabulator.min.css").read_text(encoding="utf-8")
    return js, css


_CUSTOM_CSS = """
/* Page chrome only — Tabulator's bundled midnight CSS handles the table itself. */
html, body { margin: 0; padding: 0; min-height: 100%; background: #0f1117; color: #e4e4e7; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
}

#banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    border-bottom: 1px solid #21262d;
    background: #0f1117;
    position: sticky;
    top: 0;
    z-index: 50;
}
#logo {
    color: #3eb489;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.05em;
    user-select: none;
}
#repo {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #8a94a3;
    text-decoration: none;
    font-size: 13px;
    padding: 4px 10px;
    border-radius: 4px;
}
#repo:hover { background: #1f242c; color: #e6e6e6; }
#repo svg { width: 16px; height: 16px; fill: currentColor; }

#content {
    padding: 20px 24px;
    width: 100%;
    box-sizing: border-box;
}
/* Card surface for the table — slightly elevated against page bg, with a
   subtle border and min-height that fills the viewport so short tables
   sit in a defined panel instead of floating against a vast page bg. */
#table-wrap {
    width: 100%;
    background: #131720;
    border: 1px solid #21262d;
    border-radius: 6px;
    min-height: calc(100vh - 90px);
    overflow: hidden;
}

/* Cell helpers shared across formatters. */
.trunc { cursor: pointer; }
.trunc::after { content: " …"; color: #3eb489; }
.multiline { cursor: pointer; }
.multiline::after { content: " ↵"; color: #3eb489; }
/* Boolean cells: mint check for true, dim cross for false — matches the
   terminal data browser's bool rendering. */
.bool-yes { color: #3eb489; font-size: 15px; }
.bool-no { color: #6a737d; font-size: 15px; }
/* File/PDF links: mint accent, no underline, small file icon + dim size. */
.file-link { display: inline-flex; align-items: center; gap: 6px;
    color: #3eb489; text-decoration: none; }
.file-link:hover { text-decoration: underline; }
.file-link svg { width: 14px; height: 14px; flex: none; }
.file-link .file-size { color: #6a737d; font-size: 12px; }
img { max-height: 96px; max-width: 200px; display: block; }
audio { max-width: 240px; display: block; }
/* Native audio controls are cream-colored across all browsers; flip via
   filter for the dark theme. ``hue-rotate(180)`` restores any colored
   accents (rare in audio UIs) — the net effect inverts the monochrome
   chrome (cream → dark, dark icons → light) without inverting colored
   content. Skip for video since video frames carry real color we don't
   want flipped. */
audio { filter: invert(0.92) hue-rotate(180deg); }
/* Fixed display size so the player doesn't change dimensions between
   placeholder (preload="none") and play (intrinsic source dims known).
   Without this, the cell measured against the ~240×150 placeholder
   collapses to the source's actual size when play starts and the video
   shrinks to the cell's top-left. ``object-fit: contain`` letterboxes
   sources whose aspect ratio doesn't match the box. */
video { width: 240px; height: 160px; object-fit: contain; background: #000;
    display: block; }

/* Tabulator overrides on top of midnight theme. Modern dark-app look:
   one dark base for the whole surface, subtle stripe on alternate cells,
   strong mint header with a clean underline, no per-cell vertical
   dividers. */
.tabulator,
.tabulator .tabulator-tableholder,
.tabulator .tabulator-table {
    background-color: #131720 !important;
    border: none !important;
}
/* Kill the macOS rubber-band overscroll on the body's scroll container.
   Tabulator syncs the header position from the body's scrollLeft; when
   the body bounces past its boundary the header doesn't (it's not the
   scroll target), causing a visible desync at the edges. */
.tabulator .tabulator-tableholder { overscroll-behavior: none; }

/* Header */
.tabulator .tabulator-header {
    background-color: #131720 !important;
    border-bottom: 1px solid #21262d;
}
.tabulator .tabulator-header .tabulator-col {
    background-color: transparent !important;
    border-right: 1px solid #21262d;
}
.tabulator .tabulator-header .tabulator-col:last-child { border-right: none; }
.tabulator .tabulator-header .tabulator-col,
.tabulator .tabulator-header .tabulator-col .tabulator-col-title {
    color: #3eb489;
    font-weight: 600;
    font-size: 15px;
    letter-spacing: 0.02em;
}
.tabulator .tabulator-header .tabulator-col .tabulator-col-content { padding: 12px 12px; }
.tabulator .tabulator-header .tabulator-col.tabulator-sortable:hover {
    background-color: rgba(62, 180, 137, 0.06) !important;
}

/* Rows: transparent so right-side blank space stays page-dark; zebra on
   cells only. Even row gets a very subtle lift, not a hard contrast. */
.tabulator .tabulator-row { background-color: transparent !important; border: none; }
.tabulator .tabulator-row.tabulator-row-odd .tabulator-cell { background-color: #131720; }
.tabulator .tabulator-row.tabulator-row-even .tabulator-cell { background-color: #1a1f2a; }
.tabulator .tabulator-row:hover .tabulator-cell {
    background-color: #1f2532 !important;
}
.tabulator .tabulator-row .tabulator-cell {
    color: #e4e4e7;
    border-right: none;
    border-top: none;
    padding: 6px 12px;
}
.tabulator .tabulator-row .tabulator-cell.tabulator-row-header {
    color: #6a737d;
    background-color: #131720 !important;
    border: none !important;
}
/* Kill border + frozen-column shadow on the row-number column in both
   header and body — midnight theme adds horizontal borders on row-header
   cells and a frozen-column shadow that shows as a stray vertical line
   on the left of the header. */
.tabulator .tabulator-header .tabulator-col.tabulator-row-header,
.tabulator .tabulator-frozen,
.tabulator .tabulator-row .tabulator-frozen { border: none !important;
    box-shadow: none !important; }

/* Dark scrollbars (WebKit/Blink + Firefox). */
* { scrollbar-color: #3a4049 #1a1d23; scrollbar-width: thin; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #1a1d23; }
::-webkit-scrollbar-thumb { background: #3a4049; border-radius: 5px;
    border: 2px solid #1a1d23; }
::-webkit-scrollbar-thumb:hover { background: #4a5260; }
::-webkit-scrollbar-corner { background: #1a1d23; }

/* Modal (ours, not Tabulator's). */
#modal { position: fixed; inset: 0; background: rgba(0,0,0,0.65); display: none;
    align-items: center; justify-content: center; z-index: 1000; }
#modal.open { display: flex; }
#modal-card { background: #14171c; color: #e6e6e6; border: 1px solid #2c3038;
    border-radius: 4px; max-width: 80vw; max-height: 80vh; min-width: 480px;
    display: flex; flex-direction: column;
    box-shadow: 0 12px 40px rgba(0,0,0,0.6); }
#modal-header { padding: 8px 14px; border-bottom: 1px solid #2c3038;
    display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
#modal-title { font-size: 13px; color: #8a94a3; font-family: ui-monospace, monospace; }
#modal-actions { display: flex; gap: 4px; align-items: center; }
#modal-actions button { display: inline-flex; align-items: center; gap: 6px;
    cursor: pointer; font-size: 12px; font-family: inherit;
    background: transparent; padding: 5px 10px; border-radius: 4px; }
#modal-actions button svg { width: 14px; height: 14px; stroke: currentColor;
    fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
#modal-close { color: #8a94a3; border: 1px solid transparent;
    padding: 5px 6px; }
#modal-close:hover { background: rgba(255, 255, 255, 0.06); color: #e4e4e7; }
#modal-body { padding: 12px 14px; overflow: auto; flex: 1; }
#modal-body pre { margin: 0; font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 13px; white-space: pre-wrap; word-break: break-word; color: #e6e6e6; }
#modal-body img { max-width: 76vw; max-height: 70vh; display: block; margin: 0 auto; }
"""


_INIT_JS_TEMPLATE = """
(function(){
    var data = __DATA__;
    var cols = __COLS__;

    function escapeHtml(s){
        return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    }

    var DISPLAY_CAP = __DISPLAY_CAP__;
    var formatters = {
        text: function(cell){
            var v = cell.getValue();
            if (v == null) return "";
            var s = String(v);
            var hasNewline = s.indexOf("\\n") >= 0;
            if (s.length <= DISPLAY_CAP && !hasNewline) return escapeHtml(s);
            // Show head text only; mark expandable with the .trunc class
            // (green …) for over-cap, or with the ↵ glyph for short but
            // multi-line cells. Newlines collapse in HTML, so without the
            // cue the user wouldn't know the cell has structure to expand.
            var head = s.substring(0, DISPLAY_CAP).replace(/\\n/g, " ");
            if (s.length > DISPLAY_CAP){
                return '<div class="trunc">' + escapeHtml(head) + '</div>';
            }
            return '<span class="multiline">' + escapeHtml(head) + '</span>';
        },
        media: function(cell){
            var key = cell.getField() + "_display";
            var html = cell.getRow().getData()[key];
            return html != null ? html : "";
        },
        bool: function(cell){
            var v = cell.getValue();
            if (v == null) return "";
            return v ? '<span class="bool-yes">\\u2714</span>'
                     : '<span class="bool-no">\\u2718</span>';
        }
    };

    // Tabulator's built-in ``boolean`` sorter ignores ``alignEmptyValues``,
    // so nulls end up grouped with ``false``. Substitute a custom sorter
    // that pins nulls to the bottom regardless of direction.
    function boolNullLastSorter(a, b, aRow, bRow, column, dir){
        var aNull = a == null, bNull = b == null;
        if (aNull && bNull) return 0;
        if (aNull) return dir === "asc" ? 1 : -1;
        if (bNull) return dir === "asc" ? -1 : 1;
        return (a === b) ? 0 : (a ? 1 : -1);
    }

    cols.forEach(function(col){
        if (col.sorter === "boolean") col.sorter = boolNullLastSorter;
        if (typeof col.formatter === "string" && formatters[col.formatter]){
            var name = col.formatter;
            col.formatter = formatters[name];
            if (name === "text"){
                col.cellClick = function(e, cell){
                    var v = cell.getValue();
                    if (typeof v !== "string") return;
                    if (v.length > DISPLAY_CAP || v.indexOf("\\n") >= 0){
                        openModal(cell.getColumn().getDefinition().title, v);
                    }
                };
            }
            if (name === "media"){
                col.cellClick = function(e, cell){
                    var html = cell.getRow().getData()[cell.getField() + "_display"] || "";
                    var title = cell.getColumn().getDefinition().title;
                    // Pull the ``src`` from the rendered HTML and pop the
                    // appropriate big-media element. PDFs/anchors keep the
                    // default link behavior (new tab) — no modal.
                    // Video cells skip the modal — the player's built-in
                    // fullscreen button is a better "view bigger" affordance.
                    var imgMatch = html.match(/<img[^>]*src="([^"]+)"/);
                    if (imgMatch){ openModalImage(title, imgMatch[1]); return; }
                };
            }
        }
    });

    // Sizing strategy:
    //  - ``maxHeight`` always set so the *table* scrolls internally when
    //    content exceeds the viewport (otherwise the page scrolls and
    //    the sticky header / horizontal-scroll sync break). Short content
    //    still flows naturally because the table is below the cap.
    //  - ``height`` set only for large tables to activate Tabulator's
    //    virtual scroll. Without ``height``, virtual scroll doesn't
    //    engage and 1000s of rows freeze the tab.
    var viewportCap = Math.max(240, window.innerHeight - 100);
    var tableOpts = {
        data: data,
        columns: cols,
        layout: "fitDataFill",
        renderVerticalBuffer: 600,
        movableColumns: false,
        maxHeight: viewportCap,
    };
    if (data.length > 100){
        tableOpts.height = viewportCap;
    }
    var table = new Tabulator("#table", Object.assign(tableOpts, {
        selectableRange: 1,
        selectableRangeColumns: true,
        selectableRangeRows: true,
        selectableRangeClearCells: true,
        clipboard: true,
        clipboardCopyStyled: false,
        clipboardCopyRowRange: "range",
        clipboardCopyConfig: { rowHeaders: false, columnHeaders: false },
        rowHeader: { resizable: false, frozen: true, headerSort: false,
            formatter: "rownum", hozAlign: "right", width: 50, cssClass: "tabulator-row-header" }
    }));

    // Tabulator measures columns at init, before any <img> has decoded —
    // image cells then size to just the header text. Trigger one redraw
    // after all media has loaded so column widths reflect actual content.
    // Gated on the presence of media columns: skipping the redraw on
    // text-only tables avoids a wasted re-measure pass.
    // Use ``readyState === "complete"`` as a guard against the (rare)
    // case where ``load`` already fired before we got here — late-
    // registered listeners on a one-shot event would otherwise never run.
    if (__HAS_MEDIA__){
        if (document.readyState === "complete"){
            table.redraw(true);
        } else {
            window.addEventListener("load", function(){ table.redraw(true); });
        }
    }

    var modal = document.getElementById("modal");
    var modalBody = document.getElementById("modal-body");
    var modalTitle = document.getElementById("modal-title");
    var modalClose = document.getElementById("modal-close");

    function maybeFormatJson(text){
        if (typeof text !== "string") return text;
        var trimmed = text.trim();
        if (trimmed.length < 2) return text;
        var first = trimmed[0];
        var last = trimmed[trimmed.length - 1];
        if ((first === "{" && last === "}") || (first === "[" && last === "]")){
            try { return JSON.stringify(JSON.parse(trimmed), null, 2); }
            catch (e) { /* not valid JSON, fall through */ }
        }
        return text;
    }
    function openModal(title, text){
        modalTitle.textContent = title || "";
        var pre = document.createElement("pre");
        pre.textContent = maybeFormatJson(text);
        modalBody.innerHTML = "";
        modalBody.appendChild(pre);
        modal.classList.add("open");
    }
    function openModalImage(title, src){
        modalTitle.textContent = title || "";
        modalBody.innerHTML = "";
        var img = document.createElement("img");
        img.src = src;
        modalBody.appendChild(img);
        modal.classList.add("open");
    }
    function closeModal(){
        modal.classList.remove("open");
        modalBody.innerHTML = "";
    }
    modal.addEventListener("click", function(e){ if (e.target === modal) closeModal(); });
    modalClose.addEventListener("click", closeModal);
    document.addEventListener("keydown", function(e){
        if (e.key === "Escape" && modal.classList.contains("open")) closeModal();
    });
})();
"""


def _is_numeric_dtype(series: "pd.Series") -> bool:
    """Check if a series has a numeric (non-bool) dtype."""
    import pandas as pd

    return bool(pd.api.types.is_numeric_dtype(series)) and not pd.api.types.is_bool_dtype(series)


def _is_bool_dtype(series: "pd.Series") -> bool:
    """Check if a series is bool-typed, including object columns with nulls.

    Pandas demotes ``bool`` to ``object`` dtype as soon as a None/NaN is
    present. Inspect non-null values directly so columns like
    ``[True, None, False, True]`` still route to the bool formatter.
    """
    import numpy as np
    import pandas as pd

    if pd.api.types.is_bool_dtype(series):
        return True
    if series.dtype != object:
        return False
    sample = series.dropna()
    if sample.empty:
        return False
    return bool(sample.map(lambda v: isinstance(v, (bool, np.bool_))).all())


def _coerce_text_value(value: object) -> object:
    """Normalize a non-media cell value into a JSON-serializable form for Tabulator.

    Returns ``None`` for null-likes, native types for numbers/bools, and
    strings for everything else (with a head-truncation note if the value
    exceeds ``_CELL_TEXT_HARD_CAP``).
    """
    import numpy as np
    import pandas as pd

    try:
        if value is None or pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    # ``numpy.bool_`` is *not* a subclass of Python ``bool`` in NumPy >= 1.20,
    # so check both. Without the np.bool_ branch, pandas-backed bool columns
    # fall through to ``str(value)`` and serialize as "True"/"False" strings
    # (which Tabulator's bool formatter then renders as truthy regardless).
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, indent=2, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            value = str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        # Non-media bytes (mixed columns). Show repr-ish, not raw bytes.
        raw = bytes(value)
        return f"<binary: {len(raw):,} bytes>"
    s = str(value)
    if len(s) > _CELL_TEXT_HARD_CAP:
        return s[:_CELL_TEXT_HARD_CAP] + f"\n\n... (truncated to {_CELL_TEXT_HARD_CAP:,} of {len(s):,} chars)"
    return s


def render_table_html(
    df: "pd.DataFrame",
    html_path: Path,
    *,
    title: str | None = None,
    max_rows: int = _DEFAULT_MAX_ROWS,
    inline_cap: int = _DEFAULT_INLINE_CAP,
) -> None:
    """Render ``df`` as a single HTML file at ``html_path`` using Tabulator.

    Binary-typed columns (detected by sampling) are rendered with inline
    ``<img>``/``<audio>``/``<video>`` markup. Blobs up to ``inline_cap``
    bytes are inlined as ``data:`` URIs; larger blobs are written to a
    sibling directory (``html_path.with_suffix("")``) and referenced by
    relative URL. Tables longer than ``max_rows`` are truncated (note
    propagated to the document ``<title>`` only — the page itself is just
    the table, no header chrome).

    Long text cells are display-truncated; clicking a truncated cell
    opens a modal with the full value. Numeric columns sort numerically;
    media columns are not sortable. Range-select + Cmd/Ctrl+C copies as
    TSV-compatible clipboard data via Tabulator's built-in clipboard.

    Args:
        df: DataFrame to render.
        html_path: Output HTML path. Sibling dir is derived from its stem.
        title: Document title (browser tab); defaults to the file stem.
        max_rows: Row cap. Rows past this are dropped.
        inline_cap: Per-cell size threshold for inline vs spilled rendering.
    """
    truncated_rows = max(0, len(df) - max_rows)
    view = df.head(max_rows)

    col_types: dict[str, tuple[str, str]] = {}
    for col in view.columns:
        sniffed = _sniff_column(view[col])
        if sniffed is not None:
            col_types[str(col)] = sniffed

    sib_dir = html_path.parent / html_path.stem
    sib_dir_created = False

    # Build Tabulator column defs and row data.
    column_defs: list[dict[str, object]] = []
    fields: list[tuple[str, str]] = []  # (field_name, mode) where mode in {"media","text","num","bool"}
    for col_idx, col in enumerate(view.columns):
        field = f"c{col_idx}"
        title_str = str(col)
        if title_str in col_types:
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "formatter": "media",
                    "headerSort": False,
                    "resizable": True,
                }
            )
            fields.append((field, "media"))
        elif _is_bool_dtype(view[col]):
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "formatter": "bool",
                    "sorter": "boolean",
                    "sorterParams": {"alignEmptyValues": "bottom"},
                    "hozAlign": "center",
                    "resizable": True,
                }
            )
            fields.append((field, "bool"))
        elif _is_numeric_dtype(view[col]):
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "hozAlign": "right",
                    "sorter": "number",
                    "sorterParams": {"alignEmptyValues": "bottom"},
                    "resizable": True,
                }
            )
            fields.append((field, "num"))
        else:
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "formatter": "text",
                    "sorterParams": {"alignEmptyValues": "bottom"},
                    "resizable": True,
                }
            )
            fields.append((field, "text"))

    rows: list[dict[str, object]] = []
    for row_idx in range(len(view)):
        row_data: dict[str, object] = {}
        for col_idx, (field, mode) in enumerate(fields):
            col_name = str(view.columns[col_idx])
            val = view.iloc[row_idx, col_idx]
            if mode == "media":
                blob = _extract_blob(val)
                ext, mime = col_types[col_name]
                if blob is None:
                    row_data[field] = None
                    row_data[f"{field}_display"] = ""
                    continue
                # PDFs always spill: Chrome blocks top-level navigation to
                # ``data:application/pdf`` URLs (security policy), so an
                # inlined PDF anchor opens a blank tab that only renders
                # after a manual refresh. A real ``file://`` URL works
                # cleanly. For non-PDF media the data URI is fine.
                if mime != "application/pdf" and len(blob) <= inline_cap:
                    b64 = base64.b64encode(blob).decode("ascii")
                    src = f"data:{mime};base64,{b64}"
                    row_data[field] = f"({mime})"
                    row_data[f"{field}_display"] = _render_blob(src, mime, len(blob))
                    continue
                if not sib_dir_created:
                    try:
                        sib_dir.mkdir(parents=True, exist_ok=True)
                        sib_dir_created = True
                    except OSError:
                        row_data[field] = f"<binary: {len(blob):,} bytes>"
                        row_data[f"{field}_display"] = f"<binary: {len(blob):,} bytes (write failed)>"
                        continue
                safe = _safe_col_name(col_name)
                filename = f"r{row_idx}_c{safe}{ext}"
                spill_path = sib_dir / filename
                try:
                    spill_path.write_bytes(blob)
                except OSError:
                    row_data[field] = f"<binary: {len(blob):,} bytes>"
                    row_data[f"{field}_display"] = f"<binary: {len(blob):,} bytes (write failed)>"
                    continue
                src = f"./{sib_dir.name}/{filename}"
                row_data[field] = f"({mime}, {len(blob):,} bytes)"
                row_data[f"{field}_display"] = _render_blob(src, mime, len(blob))
            else:
                row_data[field] = _coerce_text_value(val)
        rows.append(row_data)

    tabulator_js, tabulator_css = _load_tabulator_assets()
    # ``</`` inside an inline <script> string can prematurely end the tag.
    data_json = json.dumps(rows, ensure_ascii=False, default=str).replace("</", "<\\/")
    cols_json = json.dumps(column_defs, ensure_ascii=False).replace("</", "<\\/")
    init_js = (
        _INIT_JS_TEMPLATE.replace("__DATA__", data_json)
        .replace("__COLS__", cols_json)
        .replace("__DISPLAY_CAP__", str(_CELL_DISPLAY_CAP))
        .replace("__HAS_MEDIA__", "true" if col_types else "false")
    )

    doc_title = title or html_path.stem
    if truncated_rows:
        doc_title = f"{doc_title} (showing {max_rows:,} of {len(df):,} rows)"

    doc = (
        "<!doctype html><html><head><meta charset=utf-8>"
        f"<title>{html.escape(doc_title)}</title>"
        f"<style>{tabulator_css}</style>"
        f"<style>{_CUSTOM_CSS}</style>"
        f"<script>{tabulator_js}</script>"
        "</head><body>"
        '<header id="banner">'
        '<span id="logo">mintq</span>'
        '<a id="repo" href="https://github.com/megagon-internal/mintq" target="_blank" rel="noopener">'
        '<svg viewBox="0 0 16 16" aria-hidden="true">'
        '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38'
        " 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53"
        " .63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95"
        " 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68"
        " 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15"
        " 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2"
        ' 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>'
        "megagon-internal/mintq"
        "</a>"
        "</header>"
        '<main id="content"><div id="table-wrap"><div id="table"></div></div></main>'
        '<div id="modal" role="dialog" aria-hidden="true">'
        '<div id="modal-card">'
        '<div id="modal-header">'
        '<span id="modal-title"></span>'
        '<div id="modal-actions">'
        '<button id="modal-close" type="button" aria-label="Close">'
        '<svg viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>'
        "</button>"
        "</div></div>"
        '<div id="modal-body"></div>'
        "</div></div>"
        f"<script>{init_js}</script>"
        "</body></html>"
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(doc, encoding="utf-8")
