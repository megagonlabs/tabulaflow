"""Build structured table payloads for the browser output pane."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.pane.contract import ColumnDesc, MediaCell, MediaListCell, TableCardData, TableData
from tabulaflow.core.media import detect_media, extract_media_items

if TYPE_CHECKING:
    import pandas as pd


def _is_media_column(series: "pd.Series", *, sample_n: int = 5, threshold: float = 0.6) -> bool:
    """Return whether enough sampled values contain recognizable media.

    Media formats may differ between cells. The threshold avoids treating an
    ordinary mixed-value column as media because of an incidental media value.
    """
    sample = series.dropna().head(sample_n)
    if sample.empty:
        return False
    recognized = sum(extract_media_items(value, decode_plain_base64=True) is not None for value in sample)
    return recognized / len(sample) >= threshold


def _safe_col_name(name: str) -> str:
    """Sanitize a column name for use in a file path."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:32] or "col"


TABLE_RENDER_MAX_ROWS = 50_000
PANE_TABLE_MAX_HEIGHT = 640
_DEFAULT_MAX_ROWS = TABLE_RENDER_MAX_ROWS
_DEFAULT_INLINE_CAP = 256 * 1024
_CELL_TEXT_HARD_CAP = 1024 * 1024
_CELL_DISPLAY_CAP = 120


def _wire_fields(columns: list[str]) -> list[str]:
    """Return compact field ids that cannot collide with logical column names."""
    logical_names = set(columns)
    fields: list[str] = []
    for index in range(len(columns)):
        field = f"c{index}"
        while field in logical_names:
            field = f"_{field}"
        fields.append(field)
    return fields


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


def _serialize_media(
    blob: bytes,
    *,
    row_idx: int,
    col_name: str,
    item_idx: int | None,
    sib_dir: Path,
    inline_cap: int,
) -> MediaCell | str:
    detected = detect_media(blob)
    if detected is None:
        return f"<binary: {len(blob):,} bytes>"
    ext, mime = detected.suffix, detected.media_type
    if mime != "application/pdf" and len(blob) <= inline_cap:
        b64 = base64.b64encode(blob).decode("ascii")
        return {"kind": "media", "mime": mime, "src": f"data:{mime};base64,{b64}", "size": len(blob)}

    try:
        sib_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return f"<binary: {len(blob):,} bytes (write failed)>"
    safe = _safe_col_name(col_name)
    item_suffix = "" if item_idx is None else f"_i{item_idx}"
    filename = f"r{row_idx}_c{safe}{item_suffix}{ext}"
    try:
        (sib_dir / filename).write_bytes(blob)
    except OSError:
        return f"<binary: {len(blob):,} bytes (write failed)>"
    return {
        "kind": "media",
        "mime": mime,
        "src": f"./{sib_dir.name}/{filename}",
        "size": len(blob),
    }


def _build_table_data(
    df: "pd.DataFrame",
    *,
    asset_stem: str,
    output_dir: Path,
    max_rows: int = _DEFAULT_MAX_ROWS,
    inline_cap: int = _DEFAULT_INLINE_CAP,
    max_height: int | None = None,
) -> TableCardData:
    """Build the structured table payload used by output-pane cards."""
    truncated_rows = max(0, len(df) - max_rows)
    view = df.head(max_rows)

    media_columns: set[str] = set()
    for col in view.columns:
        if _is_media_column(view[col]):
            media_columns.add(str(col))

    sib_dir = output_dir / asset_stem
    column_defs: list[ColumnDesc] = []
    fields: list[tuple[str, str]] = []
    column_names = [str(col) for col in view.columns]
    wire_fields = _wire_fields(column_names)
    for col_idx, col in enumerate(view.columns):
        field = wire_fields[col_idx]
        title_str = column_names[col_idx]
        if title_str in media_columns:
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
                media_items = extract_media_items(val, decode_plain_base64=True)
                if media_items is None:
                    row_data[field] = _coerce_text_value(val)
                    continue
                items = [
                    _serialize_media(
                        blob,
                        row_idx=row_idx,
                        col_name=col_name,
                        item_idx=item_idx if len(media_items) > 1 else None,
                        sib_dir=sib_dir,
                        inline_cap=inline_cap,
                    )
                    for item_idx, blob in enumerate(media_items)
                ]
                row_data[field] = MediaListCell(kind="media-list", items=items) if len(items) > 1 else items[0]
            else:
                row_data[field] = _coerce_text_value(val)
        rows.append(row_data)

    table_payload: TableData = {
        "maxHeight": max_height,
        "displayCap": _CELL_DISPLAY_CAP,
        "meta": table_view_meta(len(df), len(df.columns), max_rows=max_rows),
        "numRows": len(df),
        "numCols": len(df.columns),
    }
    if truncated_rows:
        table_payload["truncatedRows"] = truncated_rows
        table_payload["maxRows"] = max_rows
    return {"dataset": {"rows": rows, "columns": column_defs}, "table": table_payload}


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
        A card-data fragment containing ``dataset`` and ``table``.
    """
    return _build_table_data(
        df,
        asset_stem=asset_stem,
        output_dir=output_dir,
        max_rows=max_rows,
        inline_cap=inline_cap,
        max_height=max_height,
    )
