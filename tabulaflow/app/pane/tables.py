"""Build structured table payloads for the browser output pane."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.media import sniff_binary, try_decode_base64
from tabulaflow.app.pane.types import ColumnDesc, TableCardData, TableData

if TYPE_CHECKING:
    import pandas as pd


def _extract_blob(value: object) -> bytes | None:
    """Coerce a cell value into bytes if possible.

    Handles raw bytes, HuggingFace Image/Audio structs, and base64 strings.
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


def _safe_col_name(name: str) -> str:
    """Sanitize a column name for use in a file path."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:32] or "col"


TABLE_RENDER_MAX_ROWS = 50_000
PANE_TABLE_MAX_HEIGHT = 640
_DEFAULT_MAX_ROWS = TABLE_RENDER_MAX_ROWS
_DEFAULT_INLINE_CAP = 256 * 1024
_CELL_TEXT_HARD_CAP = 1024 * 1024
_CELL_DISPLAY_CAP = 120


@dataclass(frozen=True)
class TableDataBuild:
    """Structured table payload plus Python-only field mapping."""

    data: TableCardData
    field_by_column: dict[str, str]


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}" if n == 1 else f"{n:,} {word}s"


def table_view_meta(num_rows: int, num_cols: int, *, max_rows: int = TABLE_RENDER_MAX_ROWS) -> str:
    """Return the compact row/column caption used below pane table views."""
    row_text = (
        f"showing {max_rows:,} of {_plural(num_rows, 'row')}" if num_rows > max_rows else _plural(num_rows, "row")
    )
    return f"{row_text} · {_plural(num_cols, 'column')}"


def _is_numeric_dtype(series: "pd.Series") -> bool:
    """Check if a series has a numeric (non-bool) dtype."""
    import pandas as pd

    return bool(pd.api.types.is_numeric_dtype(series)) and not pd.api.types.is_bool_dtype(series)


def _is_bool_dtype(series: "pd.Series") -> bool:
    """Check if a series is bool-typed, including object columns with nulls.

    Pandas demotes ``bool`` to ``object`` dtype as soon as a None/NaN is
    present. Inspect non-null values directly so columns like
    ``[True, None, False, True]`` still get the bool role.
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
    """Normalize a non-media cell value into a JSON-serializable form."""
    import numpy as np
    import pandas as pd

    try:
        if value is None or pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value)
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, indent=2, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            value = str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return f"<binary: {len(raw):,} bytes>"
    s = str(value)
    if len(s) > _CELL_TEXT_HARD_CAP:
        return s[:_CELL_TEXT_HARD_CAP] + f"\n\n... (truncated to {_CELL_TEXT_HARD_CAP:,} of {len(s):,} chars)"
    return s


def _build_table_data(
    df: "pd.DataFrame",
    *,
    asset_stem: str,
    output_dir: Path,
    max_rows: int = _DEFAULT_MAX_ROWS,
    inline_cap: int = _DEFAULT_INLINE_CAP,
    max_height: int | None = None,
) -> TableDataBuild:
    """Build the structured table payload used by output-pane cards."""
    truncated_rows = max(0, len(df) - max_rows)
    view = df.head(max_rows)

    col_types: dict[str, tuple[str, str]] = {}
    for col in view.columns:
        sniffed = _sniff_column(view[col])
        if sniffed is not None:
            col_types[str(col)] = sniffed

    sib_dir = output_dir / asset_stem
    sib_dir_created = False

    column_defs: list[ColumnDesc] = []
    fields: list[tuple[str, str]] = []
    field_by_column: dict[str, str] = {}
    for col_idx, col in enumerate(view.columns):
        field = f"c{col_idx}"
        title_str = str(col)
        field_by_column[title_str] = field
        if title_str in col_types:
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "role": "media",
                }
            )
            fields.append((field, "media"))
        elif _is_bool_dtype(view[col]):
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "role": "bool",
                }
            )
            fields.append((field, "bool"))
        elif _is_numeric_dtype(view[col]):
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "role": "number",
                }
            )
            fields.append((field, "number"))
        else:
            column_defs.append(
                {
                    "title": title_str,
                    "field": field,
                    "role": "text",
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
                    continue
                if mime != "application/pdf" and len(blob) <= inline_cap:
                    b64 = base64.b64encode(blob).decode("ascii")
                    src = f"data:{mime};base64,{b64}"
                    row_data[field] = {"kind": "media", "mime": mime, "src": src, "size": len(blob)}
                    continue
                if not sib_dir_created:
                    try:
                        sib_dir.mkdir(parents=True, exist_ok=True)
                        sib_dir_created = True
                    except OSError:
                        row_data[field] = f"<binary: {len(blob):,} bytes (write failed)>"
                        continue
                safe = _safe_col_name(col_name)
                filename = f"r{row_idx}_c{safe}{ext}"
                spill_path = sib_dir / filename
                try:
                    spill_path.write_bytes(blob)
                except OSError:
                    row_data[field] = f"<binary: {len(blob):,} bytes (write failed)>"
                    continue
                row_data[field] = {
                    "kind": "media",
                    "mime": mime,
                    "src": f"./{sib_dir.name}/{filename}",
                    "size": len(blob),
                }
            else:
                row_data[field] = _coerce_text_value(val)
        rows.append(row_data)

    table_payload: TableData = {
        "columns": column_defs,
        "hasMedia": bool(col_types),
        "maxHeight": max_height,
        "displayCap": _CELL_DISPLAY_CAP,
        "meta": table_view_meta(len(df), len(df.columns), max_rows=max_rows),
        "numRows": len(df),
        "numCols": len(df.columns),
    }
    if truncated_rows:
        table_payload["truncatedRows"] = truncated_rows
        table_payload["maxRows"] = max_rows
    return TableDataBuild(data={"dataset": {"rows": rows}, "table": table_payload}, field_by_column=field_by_column)


def build_table_data(
    df: "pd.DataFrame",
    *,
    asset_stem: str,
    output_dir: Path,
    max_rows: int = _DEFAULT_MAX_ROWS,
    inline_cap: int = _DEFAULT_INLINE_CAP,
    max_height: int | None = None,
) -> TableCardData:
    """Build a structured table payload for the browser pane.

    Args:
        df: DataFrame to render.
        asset_stem: Stable stem for spilled media files.
        output_dir: Directory where media spill directories are written.
        max_rows: Row cap. Rows past this are dropped.
        inline_cap: Per-cell size threshold for inline vs spilled rendering.
        max_height: Fixed pixel cap for framed table views.

    Returns:
        A record-data fragment containing ``dataset`` and ``table``.
    """
    return _build_table_data(
        df,
        asset_stem=asset_stem,
        output_dir=output_dir,
        max_rows=max_rows,
        inline_cap=inline_cap,
        max_height=max_height,
    ).data
