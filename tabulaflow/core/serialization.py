import base64
import io
import json
import math
import numbers
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

import pandas as pd


_DF_SERIALIZATION_FORMAT = "parquet_base64_v1"
_DF_SERIALIZATION_FORMAT_FEATHER = "feather_base64_v1"
_DF_PREVIEW_MAX_ROWS = 20


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of *df* with duplicate column names disambiguated.

    If columns are ``['a', 'b', 'a']`` the result is ``['a', 'b', 'a_2']``.
    Handles tricky cases like ``['a', 'b', 'a', 'a_2']`` →
    ``['a', 'b', 'a_3', 'a_2']`` (skips suffixes that collide with existing names).
    Only touches DataFrames that actually contain duplicates.
    """
    cols = [str(c) for c in df.columns]
    if len(cols) == len(set(cols)):
        return df  # nothing to do
    # Pre-reserve all original names so generated suffixes never shadow them.
    all_original = set(cols)
    used: set[str] = set()
    new_cols: list[str] = []
    for col in cols:
        if col not in used:
            used.add(col)
            new_cols.append(col)
        else:
            n = 2
            candidate = f"{col}_{n}"
            while candidate in used or candidate in all_original:
                n += 1
                candidate = f"{col}_{n}"
            used.add(candidate)
            new_cols.append(candidate)
    df = df.copy()
    df.columns = pd.Index(new_cols)
    return df


_INT64_MIN = -(2**63)
_UINT64_MAX = 2**64 - 1


def _sanitize_df_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize object-dtype columns so the DataFrame is safe for Arrow/Feather and JSON.

    Handles two classes of problems that database drivers can produce:
    * **Lone surrogates** in ``str`` values - invalid UTF-8 that crashes Feather and
      pydantic-core's JSON encoder.  Re-encoded via ``errors="replace"`` (U+FFFD).
    * **Oversized Python ints** - values outside the int64/uint64 range that Arrow
      cannot represent as C longs.  The entire column is cast to ``str`` to avoid
      mixed str/int types that Arrow also rejects.

    Only copies the DataFrame when actual changes are needed.
    """
    obj_cols = df.select_dtypes(include=["object"]).columns
    if obj_cols.empty:
        return df
    copied = False
    for col in obj_cols:
        series = df[col]

        # Check if any int overflows Arrow's int64/uint64 range.
        # If so we must stringify the whole column to keep Arrow-compatible homogeneous types.
        has_oversized_int = series.map(
            lambda v: isinstance(v, int) and not isinstance(v, bool) and not (_INT64_MIN <= v <= _UINT64_MAX)
        ).any()

        if has_oversized_int:
            sanitized = series.map(lambda v: str(v))
        else:
            # Only fix lone surrogates in str values.
            sanitized = series.map(
                lambda v: v.encode("utf-8", errors="replace").decode("utf-8") if isinstance(v, str) else v
            )
            if sanitized.equals(series):
                continue

        if not copied:
            df = df.copy()
            copied = True
        df[col] = sanitized
    return df


def _encode_nested_for_arrow(df: pd.DataFrame) -> tuple[pd.DataFrame, set[str]]:
    """JSON-stringify dict/list cells and return the names of columns touched.

    Used at the serialization boundary only. Parquet/Feather would otherwise
    infer a unified struct schema across rows for dict columns (merging keys,
    filling missing ones with NULL) and a unified element type for lists —
    destructive for heterogeneous JSON. Stringifying preserves cell values
    exactly, and the caller tags the resulting columns with ``pa.json_()`` so
    the round-trip stays self-describing.
    """
    df = df.copy()
    json_cols: set[str] = set()
    for col in df.columns:
        if df[col].dtype != object:
            continue
        if df[col].dropna().map(lambda x: isinstance(x, (dict, list))).any():
            df[col] = df[col].apply(lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list)) else x)
            json_cols.add(str(col))
    return df, json_cols


def _stringify_mixed_type_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Stringify object columns with mixed scalar types (e.g. ints + strings).

    Arrow can't infer a single type for such columns. Only touches columns
    that contain both string and non-string scalars. Preserves actual nulls.
    """
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != object:
            continue
        sample = df[col].dropna()
        if sample.empty or sample.map(lambda x: isinstance(x, str)).all():
            continue
        if sample.map(lambda x: isinstance(x, str)).any():
            # ``astype(str)`` on object columns goes through Cython's
            # ``ensure_string_array``, which UTF-8-decodes bytes values
            # instead of calling Python's ``str()``. That crashes on any
            # binary blob (PNG, etc.). ``map(str)`` uses ``bytes.__repr__``
            # safely. The outer ``where`` preserves real nulls.
            df[col] = df[col].where(df[col].isna(), df[col].map(str))
    return df


def _build_readable_df_preview(df: pd.DataFrame) -> dict[str, Any]:
    preview_df = df.head(_DF_PREVIEW_MAX_ROWS)
    # Round-trip through CSV so every column type is handled exactly like to_csv()
    # (bytes → str repr, timestamps → ISO strings, etc.) with no risk of encoding errors.
    csv_buf = io.StringIO()
    preview_df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)
    records = pd.read_csv(csv_buf).to_dict(orient="records")
    return {
        "sample_data": records,
        "num_rows": len(df),
    }


def _serialize_dataframe_legacy(df: pd.DataFrame | None) -> dict[str, Any] | None:
    """Old JSON format kept for backward compatibility fallback."""
    if df is None:
        return None
    records = df.to_dict(orient="records")
    for row in records:
        for key, val in row.items():
            if isinstance(val, pd.Timestamp):
                row[key] = val.isoformat()
            elif val is pd.NaT:
                row[key] = None
            elif isinstance(val, (bytes, bytearray)):
                row[key] = str(val)
            elif isinstance(val, str):
                row[key] = val.encode("utf-8", errors="replace").decode("utf-8")
    return {
        "schema": {
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        },
        "data": records,
    }


def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize a DataFrame for in-memory consistency.

    Dict/list cells are NOT stringified here — they keep their native Python
    types so consumers (Jinja templates, agent code) can introspect them.
    The serialization boundary (``_serialize_dataframe``) converts them to
    JSON-tagged columns when writing to Parquet.
    """
    df = _deduplicate_columns(df)
    df = _sanitize_df_strings(df)
    df = _stringify_mixed_type_columns(df)
    return df


def _coerce_for_arrow(df: pd.DataFrame) -> pd.DataFrame:
    """Cast columns that Arrow/Feather cannot handle (e.g. Neo4j graph objects) to str."""
    import pyarrow as pa

    df = df.copy()
    for col in df.columns:
        try:
            pa.array(df[col])
        except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError):
            df[col] = df[col].map(lambda v: str(v) if v is not None else None)
    return df


def _serialize_dataframe(df: pd.DataFrame | None) -> dict[str, Any] | None:
    """Serialize a DataFrame as Parquet bytes in a single JSON payload.

    Nested (dict/list) columns are JSON-encoded and tagged with ``pa.json_()``
    so each cell is a self-contained string on disk (heterogeneity-safe) but
    still carries enough metadata for ``_deserialize_dataframe`` to decode
    back to native Python objects on read.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    if df is None:
        return None
    if df.columns.empty:
        df = pd.DataFrame({"_empty": pd.Series([], dtype="object")}).iloc[:0]
    df, json_cols = _encode_nested_for_arrow(df)
    df = _coerce_for_arrow(df)
    table = pa.Table.from_pandas(df)
    if json_cols:
        new_fields = [pa.field(f.name, pa.json_()) if f.name in json_cols else f for f in table.schema]
        new_schema = pa.schema(new_fields, metadata=table.schema.metadata)
        table = pa.Table.from_pandas(df, schema=new_schema)
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "format": _DF_SERIALIZATION_FORMAT,
        "preview": _build_readable_df_preview(df),
        "parquet_base64": encoded,
    }


def _deserialize_dataframe(v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
    """Deserialize Parquet, Feather, or legacy schema+records payloads."""
    if v is None or isinstance(v, pd.DataFrame):
        return v
    if not isinstance(v, dict):
        return v

    fmt = v.get("format")

    if fmt == _DF_SERIALIZATION_FORMAT:
        import pyarrow as pa
        import pyarrow.parquet as pq

        raw = base64.b64decode(v["parquet_base64"])
        table = pq.read_table(io.BytesIO(raw))
        json_cols = [f.name for f in table.schema if isinstance(f.type, pa.JsonType)]
        df = table.to_pandas()
        for col in json_cols:
            df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
        if list(df.columns) == ["_empty"] and df.empty:
            return pd.DataFrame()
        return df

    if fmt == _DF_SERIALIZATION_FORMAT_FEATHER:
        raw = base64.b64decode(v["feather_base64"])
        import pyarrow.feather as feather

        df = feather.read_feather(io.BytesIO(raw))
        if list(df.columns) == ["_empty"] and df.empty:
            return pd.DataFrame()
        return df

    # Backward compatibility for old cached/result JSON payloads.
    dtypes = v["schema"]["dtypes"]
    df = pd.DataFrame(v["data"], columns=list(dtypes.keys()))
    return df.astype(dtypes)


def _is_missing_scalar(value: object) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def json_ready(value: object) -> object:
    """Convert data-shaped Python values into strict JSON-compatible data."""
    if value is None or _is_missing_scalar(value):
        return None
    if isinstance(value, str | bool):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, Decimal):
        return str(value) if value.is_finite() else None
    if isinstance(value, Mapping):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_ready(item) for item in value]
    return value


def dumps_strict_json(data: object) -> str:
    """Serialize as standards-compliant JSON, never emitting NaN or Infinity."""
    return json.dumps(json_ready(data), ensure_ascii=False, default=str, allow_nan=False)
