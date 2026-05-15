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
    """Coerce a cell value into bytes if possible (handles base64 strings)."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
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


def _render_blob(src: str, mime: str, size: int) -> str:
    """Render a blob reference as inline media markup.

    ``src`` is either a ``data:`` URI (inline) or a relative file URL
    (spilled to sibling file). Same markup either way; only the src
    differs.
    """
    if mime.startswith("image/"):
        return f'<img src="{src}" loading="lazy">'
    if mime.startswith("audio/"):
        return f'<audio controls preload="none" src="{src}"></audio>'
    if mime.startswith("video/"):
        return f'<video controls preload="none" src="{src}"></video>'
    if mime == "application/pdf":
        return f'<a href="{src}" target="_blank">PDF ({size:,} bytes)</a>'
    return f'<a href="{src}">binary ({size:,} bytes)</a>'


def _safe_col_name(name: str) -> str:
    """Sanitize a column name for use in a file path."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:32] or "col"


_DEFAULT_MAX_ROWS = 50_000
_DEFAULT_INLINE_CAP = 256 * 1024  # 256 KB
# Cap on the full text stored per non-media cell (sent to Tabulator's data
# array). Truncated text above this is replaced with a head excerpt + note;
# users can press `b` on the source row/cell for full content.
_CELL_TEXT_HARD_CAP = 64 * 1024
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
html, body { margin: 0; padding: 0; background: #0d0f12; min-height: 100%; }
body {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    color: #d8d8d8;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px;
    min-height: calc(100vh - 48px);
    box-sizing: border-box;
}
#banner {
    color: #3eb489;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.45em;
    margin: 0 0 16px 0;
    text-transform: lowercase;
    user-select: none;
}
#banner::before { content: "» "; opacity: 0.6; }
#banner::after { content: " «"; opacity: 0.6; }
#table-wrap {
    max-width: 96vw;
    border: 1px solid #3eb489;
    border-radius: 3px;
    background: #0d0f12;
    overflow: hidden;
}
#table { max-height: calc(100vh - 120px); }

/* Tabulator base */
.tabulator {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 15px;
    border: none;
    background: transparent;
}
.tabulator-row { color: #d8d8d8; background: transparent; border-bottom: none; }
.tabulator-row.tabulator-row-even { background-color: transparent; }
.tabulator-row .tabulator-cell {
    border-right: none;
    border-top: none;
    padding: 4px 14px;
    background: transparent;
}
.tabulator-row.tabulator-selectable:hover { background-color: rgba(62, 180, 137, 0.05); cursor: default; }
.tabulator-row .tabulator-cell.tabulator-row-header,
.tabulator-row-header { color: #5a6470; }

/* Header row: green text, mint underline, no per-cell vertical borders */
.tabulator .tabulator-header {
    background: transparent;
    border-bottom: 1px solid #3eb489;
}
.tabulator .tabulator-header .tabulator-col {
    background: transparent;
    color: #3eb489;
    font-weight: 700;
    border-right: none;
    padding: 8px 14px;
}
.tabulator .tabulator-header .tabulator-col.tabulator-sortable:hover {
    background: rgba(62, 180, 137, 0.08);
}
.tabulator .tabulator-header .tabulator-col .tabulator-col-content { padding: 0; }

/* Range selection — mint highlight, dark text on focused cell */
.tabulator-row .tabulator-cell.tabulator-range-selected:not(.tabulator-range-only-cell-selected) {
    background: rgba(62, 180, 137, 0.18);
}
.tabulator-row .tabulator-cell.tabulator-range-only-cell-selected,
.tabulator .tabulator-header .tabulator-col.tabulator-range-highlight.tabulator-range-selected {
    background: #3eb489;
    color: #0d0f12;
}

/* Scrollbars (Tabulator's holder) */
.tabulator .tabulator-tableholder::-webkit-scrollbar { width: 10px; height: 10px; }
.tabulator .tabulator-tableholder::-webkit-scrollbar-thumb { background: #2c3038; border-radius: 5px; }
.tabulator .tabulator-tableholder::-webkit-scrollbar-thumb:hover { background: #3eb489; }
.tabulator .tabulator-tableholder::-webkit-scrollbar-track { background: transparent; }

/* Cell content helpers */
.trunc { cursor: pointer; color: inherit; }
.trunc::after { content: " …"; color: #3eb489; }
.null { color: #5a6470; font-style: italic; }
img { max-height: 96px; max-width: 200px; display: block; border-radius: 2px; }
audio, video { max-width: 240px; display: block; }
a { color: #3eb489; }

/* Modal */
#modal { position: fixed; inset: 0; background: rgba(0,0,0,0.65); display: none;
    align-items: center; justify-content: center; z-index: 1000; }
#modal.open { display: flex; }
#modal-card { background: #14171c; color: #d8d8d8; border: 1px solid #3eb489;
    border-radius: 4px; max-width: 80vw; max-height: 80vh; min-width: 480px;
    display: flex; flex-direction: column;
    box-shadow: 0 12px 40px rgba(0,0,0,0.6); }
#modal-header { padding: 8px 14px; border-bottom: 1px solid #2c3038;
    display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
#modal-title { font-size: 14px; color: #3eb489;
    font-family: ui-monospace, "SF Mono", Menlo, monospace; }
#modal-actions { display: flex; gap: 8px; }
#modal-actions button { background: transparent; color: #d8d8d8;
    border: 1px solid #3a4049; padding: 4px 14px; border-radius: 3px;
    cursor: pointer; font-size: 13px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace; }
#modal-actions button:hover { background: #1f242c; border-color: #3eb489; color: #3eb489; }
#modal-body { padding: 14px 16px; overflow: auto; flex: 1; }
#modal-body pre { margin: 0; font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 14px; white-space: pre-wrap; word-break: break-word; color: #d8d8d8; }
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
            if (v == null) return '<span class="null">—</span>';
            var s = String(v);
            if (s.length <= DISPLAY_CAP) return escapeHtml(s);
            var head = s.substring(0, DISPLAY_CAP).replace(/\\n/g, " ");
            return '<div class="trunc">' + escapeHtml(head) + '</div>';
        },
        media: function(cell){
            var key = cell.getField() + "_display";
            var html = cell.getRow().getData()[key];
            return html != null ? html : "";
        }
    };

    cols.forEach(function(col){
        if (typeof col.formatter === "string" && formatters[col.formatter]){
            var name = col.formatter;
            col.formatter = formatters[name];
            if (name === "text"){
                col.cellClick = function(e, cell){
                    var v = cell.getValue();
                    if (typeof v === "string" && v.length > DISPLAY_CAP){
                        openModal(cell.getColumn().getDefinition().title, v);
                    }
                };
            }
        }
    });

    var table = new Tabulator("#table", {
        data: data,
        columns: cols,
        maxHeight: "calc(100vh - 120px)",
        layout: "fitData",
        renderVerticalBuffer: 600,
        movableColumns: false,
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
    });

    var modal = document.getElementById("modal");
    var modalBody = document.getElementById("modal-body");
    var modalTitle = document.getElementById("modal-title");
    var modalCopy = document.getElementById("modal-copy");
    var modalClose = document.getElementById("modal-close");

    function openModal(title, text){
        modalTitle.textContent = title || "";
        var pre = document.createElement("pre");
        pre.textContent = text;
        modalBody.innerHTML = "";
        modalBody.appendChild(pre);
        modal.classList.add("open");
    }
    function closeModal(){ modal.classList.remove("open"); }
    modal.addEventListener("click", function(e){ if (e.target === modal) closeModal(); });
    modalClose.addEventListener("click", closeModal);
    modalCopy.addEventListener("click", function(){
        var text = modalBody.textContent || "";
        if (navigator.clipboard){ navigator.clipboard.writeText(text); }
        modalCopy.textContent = "copied";
        setTimeout(function(){ modalCopy.textContent = "copy"; }, 1200);
    });
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
    """Check if a series has a bool dtype."""
    import pandas as pd

    return bool(pd.api.types.is_bool_dtype(series))


def _coerce_text_value(value: object) -> object:
    """Normalize a non-media cell value into a JSON-serializable form for Tabulator.

    Returns ``None`` for null-likes, native types for numbers/bools, and
    strings for everything else (with a head-truncation note if the value
    exceeds ``_CELL_TEXT_HARD_CAP``).
    """
    import pandas as pd

    try:
        if value is None or pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return value
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
                    "formatter": "tickCross",
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
                if len(blob) <= inline_cap:
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
        '<div id="banner">mintq</div>'
        '<div id="table-wrap"><div id="table"></div></div>'
        '<div id="modal" role="dialog" aria-hidden="true">'
        '<div id="modal-card">'
        '<div id="modal-header">'
        '<span id="modal-title"></span>'
        '<div id="modal-actions">'
        '<button id="modal-copy" type="button">copy</button>'
        '<button id="modal-close" type="button">close</button>'
        "</div></div>"
        '<div id="modal-body"></div>'
        "</div></div>"
        f"<script>{init_js}</script>"
        "</body></html>"
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(doc, encoding="utf-8")
