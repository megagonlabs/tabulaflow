"""Strict JSON conversion for data-shaped values."""

import json
import math
import numbers
from collections.abc import Mapping, Sequence
from decimal import Decimal

import pandas as pd


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
    return str(value)


def dumps_strict_json(data: object) -> str:
    """Serialize as standards-compliant JSON, never emitting NaN or Infinity."""
    return json.dumps(json_ready(data), ensure_ascii=False, allow_nan=False)


__all__ = ["dumps_strict_json", "json_ready"]
