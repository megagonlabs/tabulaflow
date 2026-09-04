"""Define the canonical form and persistence format for result DataFrames.

Database connectors produce pandas DataFrames with varying indexes, column names,
dtypes, and object-cell values. This module gives the rest of TabulaFlow one stable
contract: unique string column names, a fresh ``RangeIndex``, and portable Python
values. Normalization always returns a copy.

The core abstractions are:

* ``_normalize_dataframe`` establishes the in-memory contract.
* ``serialize_dataframe`` and ``deserialize_dataframe`` provide a lossless,
  versioned Parquet representation.
* ``SerializableDataFrame`` applies that representation to Pydantic models.

Arrow-compatible columns remain native Parquet columns. Heterogeneous object
columns use a tagged JSON codec recorded in field metadata. Schema metadata
identifies the overall format and preserves the row count of zero-column results.
"""

from __future__ import annotations

import base64
import io
import json
import math
import numbers
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated, TypeAlias
from uuid import UUID

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BeforeValidator, PlainSerializer

_DATAFRAME_FORMAT = "parquet_v1"
_FORMAT_KEY = b"tabulaflow.dataframe.format"
_ROW_COUNT_KEY = b"tabulaflow.dataframe.row_count"
_CODEC_KEY = b"tabulaflow.dataframe.codec"
_TAGGED_JSON_CODEC = b"tagged_json_v1"


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _validate_utf8(value: str, path: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{path} contains text that is not valid UTF-8") from exc


def _column_names(columns: pd.Index) -> list[str]:
    """Stringify and deduplicate names without colliding with existing names."""
    original = [str(column) for column in columns]
    for name in original:
        _validate_utf8(name, "column name")
    reserved = set(original)
    used: set[str] = set()
    names: list[str] = []
    for name in original:
        if name not in used:
            candidate = name
        else:
            suffix = 2
            candidate = f"{name}_{suffix}"
            while candidate in used or candidate in reserved:
                suffix += 1
                candidate = f"{name}_{suffix}"
        used.add(candidate)
        names.append(candidate)
    return names


def _normalize_value(value: object, path: str) -> object:
    """Normalize one object-cell value or reject it with its location."""
    if _is_missing(value):
        return None
    if isinstance(value, str):
        _validate_utf8(value, path)
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, np.ndarray):
        return _normalize_value(value.tolist(), path)
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value)
    if isinstance(value, np.timedelta64):
        return pd.Timedelta(value)
    if isinstance(value, np.generic):
        return _normalize_value(value.item(), path)
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string mapping key")
            normalized[key] = _normalize_value(item, f"{path}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(
        value,
        (bool, numbers.Integral, numbers.Real, Decimal, bytes, datetime, date, time, timedelta, UUID),
    ):
        return value
    raise ValueError(f"{path} has unsupported value type {type(value).__name__}")


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Copy and normalize a query-result DataFrame.

    Missing object values become ``None``; NumPy values become portable Python
    values; byte-like values become ``bytes``; tuples become lists; and mapping
    keys must be strings. Text must be valid UTF-8 and unsupported objects are
    rejected.

    Args:
        df: DataFrame to normalize.

    Returns:
        A normalized copy with unique string columns and a fresh ``RangeIndex``.

    Raises:
        TypeError: If ``df`` is not a pandas DataFrame.
        ValueError: If a value is unsupported or violates the data contract.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"expected pandas DataFrame, got {type(df).__name__}")
    normalized = df.copy()
    normalized.columns = pd.Index(_column_names(normalized.columns))
    normalized.reset_index(drop=True, inplace=True)
    object_columns = set(normalized.select_dtypes(include=["object"]).columns)
    for column in object_columns:
        values = [
            _normalize_value(value, f"column {column!r}, row {row}") for row, value in enumerate(normalized[column])
        ]
        normalized[column] = pd.Series(values, index=normalized.index, dtype=object)
    for column in normalized.columns:
        if column in object_columns:
            continue
        if pd.api.types.is_string_dtype(normalized[column].dtype) or isinstance(
            normalized[column].dtype, pd.CategoricalDtype
        ):
            for row, value in enumerate(normalized[column]):
                if isinstance(value, str):
                    _normalize_value(value, f"column {column!r}, row {row}")
    return normalized


def _encode_value(value: object) -> list[object]:
    """Encode one value as a reversible JSON tag and payload."""
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, numbers.Integral):
        return ["int", str(int(value))]
    if isinstance(value, numbers.Real):
        numeric = float(value)
        if math.isnan(numeric):
            return ["float", "nan"]
        if math.isinf(numeric):
            return ["float", "inf" if numeric > 0 else "-inf"]
        return ["float", repr(numeric)]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, bytes):
        return ["bytes", base64.b64encode(value).decode("ascii")]
    if isinstance(value, pd.Timestamp):
        return ["timestamp", value.isoformat()]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, time):
        return ["time", value.isoformat()]
    if isinstance(value, pd.Timedelta):
        return ["timedelta_ns", str(value.value)]
    if isinstance(value, timedelta):
        microseconds = (value.days * 86_400 + value.seconds) * 1_000_000 + value.microseconds
        return ["timedelta_us", str(microseconds)]
    if isinstance(value, UUID):
        return ["uuid", str(value)]
    if isinstance(value, dict):
        return ["dict", [[key, _encode_value(item)] for key, item in value.items()]]
    if isinstance(value, list):
        return ["list", [_encode_value(item) for item in value]]
    raise TypeError(f"unexpected normalized value type {type(value).__name__}")


def _tagged_pair(value: object) -> tuple[str, object | None]:
    if not isinstance(value, list) or not value or not isinstance(value[0], str) or len(value) > 2:
        raise ValueError("invalid tagged value")
    return value[0], value[1] if len(value) == 2 else None


def _decode_value(value: object) -> object:
    """Decode and validate one tagged fallback value."""
    tag, payload = _tagged_pair(value)
    if tag == "null" and payload is None:
        return None
    if tag == "bool" and isinstance(payload, bool):
        return payload
    if tag == "int" and isinstance(payload, str):
        return int(payload)
    if tag == "float" and isinstance(payload, str):
        return float(payload)
    if tag == "decimal" and isinstance(payload, str):
        return Decimal(payload)
    if tag == "str" and isinstance(payload, str):
        return payload
    if tag == "bytes" and isinstance(payload, str):
        return base64.b64decode(payload, validate=True)
    if tag == "timestamp" and isinstance(payload, str):
        return pd.Timestamp(payload)
    if tag == "datetime" and isinstance(payload, str):
        return datetime.fromisoformat(payload)
    if tag == "date" and isinstance(payload, str):
        return date.fromisoformat(payload)
    if tag == "time" and isinstance(payload, str):
        return time.fromisoformat(payload)
    if tag == "timedelta_ns" and isinstance(payload, str):
        return pd.Timedelta(int(payload), unit="ns")
    if tag == "timedelta_us" and isinstance(payload, str):
        return timedelta(microseconds=int(payload))
    if tag == "uuid" and isinstance(payload, str):
        return UUID(payload)
    if tag == "list" and isinstance(payload, list):
        return [_decode_value(item) for item in payload]
    if tag == "dict" and isinstance(payload, list):
        result: dict[str, object] = {}
        for item in payload:
            if not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str):
                raise ValueError("invalid tagged dictionary")
            if item[0] in result:
                raise ValueError("duplicate tagged dictionary key")
            result[item[0]] = _decode_value(item[1])
        return result
    raise ValueError(f"invalid tagged {tag!r} value")


def _matches_inferred_type(value: object, data_type: pa.DataType) -> bool:
    """Return whether Arrow inferred ``data_type`` without coercing ``value``."""
    if _is_missing(value):
        return True
    if pa.types.is_struct(data_type):
        if not isinstance(value, Mapping) or list(value) != [field.name for field in data_type]:
            return False
        return all(_matches_inferred_type(value[field.name], field.type) for field in data_type)
    if pa.types.is_list(data_type) or pa.types.is_large_list(data_type) or pa.types.is_fixed_size_list(data_type):
        return isinstance(value, list) and all(_matches_inferred_type(item, data_type.value_type) for item in value)
    if pa.types.is_binary(data_type) or pa.types.is_large_binary(data_type):
        return isinstance(value, bytes)
    if pa.types.is_string(data_type) or pa.types.is_large_string(data_type):
        return isinstance(value, str)
    if pa.types.is_boolean(data_type):
        return isinstance(value, bool)
    if pa.types.is_integer(data_type):
        return isinstance(value, numbers.Integral) and not isinstance(value, bool)
    if pa.types.is_floating(data_type):
        return isinstance(value, numbers.Real) and not isinstance(value, numbers.Integral)
    if pa.types.is_decimal(data_type):
        return isinstance(value, Decimal)
    if pa.types.is_timestamp(data_type):
        return isinstance(value, (pd.Timestamp, datetime))
    if pa.types.is_date(data_type):
        return isinstance(value, date) and not isinstance(value, datetime)
    if pa.types.is_time(data_type):
        return isinstance(value, time)
    if pa.types.is_duration(data_type):
        return isinstance(value, (pd.Timedelta, timedelta))
    return False


def _native_arrow_array(series: pd.Series, column: str) -> pa.Array:
    """Encode a typed pandas column as Arrow or fail clearly."""
    try:
        return pa.array(series, from_pandas=True)
    except (pa.ArrowException, OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"column {column!r} with dtype {series.dtype} cannot be encoded as Arrow") from exc


def _inferred_object_array(series: pd.Series) -> pa.Array | None:
    """Return an object column as Arrow only when inference is lossless."""
    try:
        array = pa.array(series, from_pandas=True)
    except (pa.ArrowException, OverflowError, TypeError, ValueError):
        return None
    if all(_matches_inferred_type(value, array.type) for value in series):
        return array
    return None


def _fallback_arrow_array(series: pd.Series, column: str) -> tuple[pa.Array, pa.Field]:
    """Encode a normalized object column with the tagged JSON codec."""
    encoded = [
        None if value is None else json.dumps(_encode_value(value), ensure_ascii=False, separators=(",", ":"))
        for value in series
    ]
    array = pa.array(encoded, type=pa.large_string())
    return array, pa.field(column, array.type, metadata={_CODEC_KEY: _TAGGED_JSON_CODEC})


def _arrow_column(series: pd.Series, column: str) -> tuple[pa.Array, pa.Field]:
    """Select native or fallback Arrow storage for one column."""
    if series.dtype != object:
        array = _native_arrow_array(series, column)
        return array, pa.field(column, array.type)
    array = _inferred_object_array(series)
    if array is not None:
        return array, pa.field(column, array.type)
    return _fallback_arrow_array(series, column)


def serialize_dataframe(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to self-describing Parquet bytes.

    The DataFrame is normalized first. For object columns, native Arrow types
    are used only when their inferred shape matches every source value;
    otherwise the column uses the reversible tagged JSON fallback.

    Args:
        df: DataFrame to serialize.

    Returns:
        Versioned Parquet bytes.

    Raises:
        TypeError: If ``df`` is not a pandas DataFrame.
        ValueError: If the DataFrame contains unsupported values.
    """
    normalized = _normalize_dataframe(df)
    arrays: list[pa.Array] = []
    fields: list[pa.Field] = []
    for column in normalized.columns:
        array, field = _arrow_column(normalized[column], str(column))
        arrays.append(array)
        fields.append(field)
    metadata = {
        _FORMAT_KEY: _DATAFRAME_FORMAT.encode("ascii"),
        _ROW_COUNT_KEY: str(len(normalized)).encode("ascii"),
    }
    table = pa.Table.from_arrays(arrays, schema=pa.schema(fields, metadata=metadata))
    output = io.BytesIO()
    pq.write_table(table, output)
    return output.getvalue()


def _read_parquet(payload: bytes) -> pa.Table:
    """Read a Parquet payload with a stable public error."""
    try:
        return pq.read_table(io.BytesIO(payload))
    except pa.ArrowException as exc:
        raise ValueError("invalid DataFrame Parquet payload") from exc


def _parse_metadata(table: pa.Table) -> tuple[int, list[str]]:
    """Validate format metadata and return reconstruction details."""
    metadata = table.schema.metadata or {}
    if metadata.get(_FORMAT_KEY) != _DATAFRAME_FORMAT.encode("ascii"):
        raise ValueError("unsupported DataFrame format")
    try:
        row_count = int(metadata[_ROW_COUNT_KEY])
    except (KeyError, ValueError) as exc:
        raise ValueError("invalid DataFrame Parquet metadata") from exc
    if row_count < 0 or (table.column_names and table.num_rows != row_count):
        raise ValueError("invalid DataFrame Parquet row count")
    fallback_columns: list[str] = []
    for field in table.schema:
        codec = field.metadata.get(_CODEC_KEY) if field.metadata else None
        if codec is not None and codec != _TAGGED_JSON_CODEC:
            raise ValueError(f"unsupported fallback codec in column {field.name!r}")
        if codec == _TAGGED_JSON_CODEC:
            fallback_columns.append(field.name)
    return row_count, fallback_columns


def _decode_table(table: pa.Table, row_count: int, fallback_columns: list[str]) -> pd.DataFrame:
    """Convert an Arrow table and decode tagged fallback columns."""
    if not table.column_names:
        # Parquet cannot represent the row count of a table with no columns.
        return pd.DataFrame(index=pd.RangeIndex(row_count))
    df = table.to_pandas()
    for column in fallback_columns:
        try:
            values = [None if value is None else _decode_value(json.loads(value)) for value in df[column]]
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid fallback values in column {column!r}") from exc
        df[column] = pd.Series(values, index=df.index, dtype=object)
    return df


def deserialize_dataframe(payload: bytes) -> pd.DataFrame:
    """Deserialize bytes produced by :func:`serialize_dataframe`.

    Args:
        payload: Versioned Parquet bytes.

    Returns:
        A normalized DataFrame.

    Raises:
        ValueError: If the payload, metadata, or fallback values are invalid or
            use an unsupported version.
    """
    table = _read_parquet(payload)
    row_count, fallback_columns = _parse_metadata(table)
    return _normalize_dataframe(_decode_table(table, row_count, fallback_columns))


def _deserialize_adapter(value: object) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return _normalize_dataframe(value)
    if not isinstance(value, dict) or value.get("format") != _DATAFRAME_FORMAT:
        raise ValueError("invalid DataFrame payload")
    encoded = value.get("parquet_base64")
    if not isinstance(encoded, str):
        raise ValueError("invalid DataFrame payload")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError("invalid DataFrame payload") from exc
    return deserialize_dataframe(payload)


def _serialize_adapter(df: pd.DataFrame) -> dict[str, str]:
    return {
        "format": _DATAFRAME_FORMAT,
        "parquet_base64": base64.b64encode(serialize_dataframe(df)).decode("ascii"),
    }


SerializableDataFrame: TypeAlias = Annotated[
    pd.DataFrame,
    BeforeValidator(_deserialize_adapter),
    PlainSerializer(_serialize_adapter, return_type=dict[str, str], when_used="always"),
]


__all__ = ["SerializableDataFrame", "deserialize_dataframe", "serialize_dataframe"]
