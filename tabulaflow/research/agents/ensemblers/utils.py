"""Shared execution-result helpers for research ensemblers."""

from typing import Any

import pandas as pd

from tabulaflow.output.formatting import format_dataframe

_FLOAT_ROUND_DIGITS = 6


def _normalize_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return "<NULL>"
    if isinstance(value, float):
        return str(round(value, _FLOAT_ROUND_DIGITS))
    return str(value)


def execution_result_key(df: pd.DataFrame) -> tuple[tuple[str, ...], ...]:
    """Return the ensembler's order-independent, duplicate-insensitive result key."""
    df = df.reindex(sorted(df.columns), axis=1)
    rows = [tuple(_normalize_value(value) for value in row) for row in df.itertuples(index=False, name=None)]
    return tuple(sorted(set(rows)))


def format_execution_result(df: pd.DataFrame, max_rows: int = 10) -> str:
    """Format a candidate result for an ensembler prompt."""
    if df.empty:
        return "(empty result)"
    return f"{format_dataframe(df, max_visible_rows=max_rows)}\n({len(df)} rows)"
