import pandas as pd
from decimal import Decimal
from pandas.testing import assert_frame_equal
import pytest

from tabulaflow.core.serialization import (
    _DF_SERIALIZATION_FORMAT,
    _DF_SERIALIZATION_FORMAT_FEATHER,
    _deserialize_dataframe,
    _sanitize_df,
    _serialize_dataframe,
)
from tabulaflow.core import ExecResult


def test_dataframe_round_trip_parquet_payload() -> None:
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "score": [1.25, 2.5, 3.75],
            "label": ["a", "b", "c"],
            "amount": [Decimal("1.23"), Decimal("4.56"), Decimal("7.89")],
        }
    )
    df.index = pd.Index(["k1", "k2", "k3"], name="row_key")

    serialized = _serialize_dataframe(df)
    assert serialized is not None
    assert serialized["format"] == _DF_SERIALIZATION_FORMAT
    assert "parquet_base64" in serialized
    assert serialized["preview"]["num_rows"] == 3
    assert len(serialized["preview"]["sample_data"]) == 3

    deserialized = _deserialize_dataframe(serialized)
    assert deserialized is not None
    assert_frame_equal(df, deserialized, check_dtype=True, check_index_type=True)
    assert all(isinstance(v, Decimal) for v in deserialized["amount"])


def test_dataframe_deserialize_feather_payload() -> None:
    """Feather payloads from older caches should still deserialize."""
    import base64
    import io

    import pyarrow.feather as feather

    df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
    buf = io.BytesIO()
    feather.write_feather(df, buf)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

    payload = {
        "format": _DF_SERIALIZATION_FORMAT_FEATHER,
        "feather_base64": encoded,
    }

    deserialized = _deserialize_dataframe(payload)
    assert deserialized is not None
    assert_frame_equal(df, deserialized, check_dtype=True)


def test_dataframe_deserialize_legacy_payload() -> None:
    legacy_payload = {
        "schema": {"dtypes": {"x": "int64", "y": "object"}},
        "data": [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}],
    }

    deserialized = _deserialize_dataframe(legacy_payload)
    expected = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
    expected = expected.astype({"x": "int64", "y": "object"})
    assert_frame_equal(expected, deserialized, check_dtype=True)


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"format": "unknown"},
        {"format": _DF_SERIALIZATION_FORMAT},
        {"format": _DF_SERIALIZATION_FORMAT, "parquet_base64": "not base64"},
        {"format": _DF_SERIALIZATION_FORMAT_FEATHER},
        {"format": _DF_SERIALIZATION_FORMAT_FEATHER, "feather_base64": "not base64"},
    ],
)
def test_dataframe_deserialize_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError, match="invalid DataFrame payload"):
        _deserialize_dataframe(payload)


def test_dataframe_round_trip_nested_columns() -> None:
    """Nested dicts/lists round-trip as native Python objects (no key merging)."""
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "meta": [{"a": 1, "b": 2}, {"a": 3, "c": 4}],
            "tags": [["x", "y"], ["z"]],
        }
    )

    sanitized = _sanitize_df(df)
    serialized = _serialize_dataframe(sanitized)
    deserialized = _deserialize_dataframe(serialized)

    assert deserialized is not None
    assert deserialized.loc[0, "meta"] == {"a": 1, "b": 2}
    assert deserialized.loc[1, "meta"] == {"a": 3, "c": 4}
    assert deserialized.loc[0, "tags"] == ["x", "y"]
    assert deserialized.loc[1, "tags"] == ["z"]


def test_dataframe_sanitization_does_not_copy_regular_input() -> None:
    df = pd.DataFrame({"id": [1, 2], "label": ["a", "b"]})

    assert _sanitize_df(df) is df


def test_dataframe_sanitization_copies_before_stringifying_mixed_column() -> None:
    df = pd.DataFrame({"mixed": ["a", 1, None]})

    sanitized = _sanitize_df(df)

    assert sanitized is not df
    assert sanitized["mixed"].tolist() == ["a", "1", None]
    assert df["mixed"].tolist() == ["a", 1, None]


def test_dataframe_sanitization_preserves_nulls_with_oversized_integers() -> None:
    df = pd.DataFrame({"value": [2**100, None]}, dtype=object)

    sanitized = _sanitize_df(df)

    assert sanitized["value"].tolist() == [str(2**100), None]


def test_exec_result_json_round_trip_dataframe() -> None:
    df = pd.DataFrame(
        {
            "value": [Decimal("10.5"), Decimal("20.25"), None],
            "created_at": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        }
    )

    result = ExecResult(df=df)
    payload = result.model_dump_json()
    loaded = ExecResult.model_validate_json(payload)

    assert loaded.df is not None
    assert_frame_equal(df, loaded.df, check_dtype=True)
    assert isinstance(loaded.df.loc[0, "value"], Decimal)
    assert isinstance(loaded.df.loc[1, "value"], Decimal)


def test_exec_result_accepts_mixed_bytes_and_str() -> None:
    """``_stringify_mixed_type_columns`` must not crash on bytes payloads.

    Regression: pandas' ``astype(str)`` UTF-8-decodes bytes via the Cython
    string-array path. Mixed bytes+str columns (e.g. a BLOB cell alongside
    text rows) must stringify via Python ``str()`` instead.
    """
    df = pd.DataFrame(
        {
            "mixed": [b"\x89PNG\r\n\x1a\n", "plain text", 42, None, "another"],
        }
    )
    result = ExecResult(df=df)
    assert result.df is not None
    values = result.df["mixed"].tolist()
    assert values[0].startswith("b'\\x89PNG")
    assert values[1] == "plain text"
    assert values[2] == "42"
    assert values[3] is None
    assert values[4] == "another"
