import base64
from decimal import Decimal
import io

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pyarrow.parquet as pq
import pytest

from tabulaflow.core import ExecResult
from tabulaflow.core.dataframe import deserialize_dataframe, serialize_dataframe


def test_dataframe_round_trip_uses_parquet_and_discards_index() -> None:
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "score": [1.25, 2.5, 3.75],
            "label": ["a", "b", "c"],
            "amount": [Decimal("1.23"), Decimal("4.56"), Decimal("7.89")],
        },
        index=pd.Index(["k1", "k2", "k3"], name="row_key"),
    )

    payload = serialize_dataframe(df)
    table = pq.read_table(io.BytesIO(payload))
    loaded = deserialize_dataframe(payload)

    assert table.schema.metadata[b"tabulaflow.dataframe.format"] == b"parquet_v1"
    assert_frame_equal(loaded, df.reset_index(drop=True), check_dtype=True)
    assert all(isinstance(value, Decimal) for value in loaded["amount"])


def test_dataframe_normalization_makes_column_names_unique_strings() -> None:
    df = pd.DataFrame([[1, 2, 3, 4]], columns=[1, "a", 1, "1_2"])

    normalized = ExecResult(df=df).df

    assert normalized is not None
    assert normalized.columns.tolist() == ["1", "a", "1_3", "1_2"]
    assert isinstance(normalized.index, pd.RangeIndex)


def test_dataframe_normalization_preserves_object_dtype() -> None:
    df = pd.DataFrame({"mixed": pd.Series([1, 1.5], dtype=object)})

    normalized = ExecResult(df=df).df

    assert normalized is not None
    assert normalized["mixed"].dtype == object
    assert normalized["mixed"].tolist() == [1, 1.5]


def test_dataframe_round_trip_preserves_zero_column_shape() -> None:
    df = pd.DataFrame(index=pd.RangeIndex(3))

    loaded = deserialize_dataframe(serialize_dataframe(df))

    assert loaded.shape == (3, 0)


def test_dataframe_round_trip_preserves_irregular_nested_values() -> None:
    df = pd.DataFrame(
        {
            "meta": [{"a": 1, "b": 2}, {"a": 3, "c": 4}],
            "items": [[1, "two", b"three"], None],
        }
    )

    loaded = deserialize_dataframe(serialize_dataframe(df))

    assert loaded.to_dict(orient="records") == df.to_dict(orient="records")


def test_dataframe_round_trip_preserves_native_list_column() -> None:
    values = [[1, 2], [3, 4]]
    df = pd.DataFrame({"items": values}, dtype=object)

    payload = serialize_dataframe(df)
    table = pq.read_table(io.BytesIO(payload))
    loaded = deserialize_dataframe(payload)

    assert table.schema.field("items").metadata is None
    assert loaded["items"].tolist() == values


def test_dataframe_round_trip_preserves_native_hf_media_struct() -> None:
    image = b"\x89PNG\r\n\x1a\n"
    df = pd.DataFrame(
        {
            "image": [
                {"bytes": image, "path": None},
                {"bytes": None, "path": "image.png"},
            ]
        }
    )

    payload = serialize_dataframe(df)
    table = pq.read_table(io.BytesIO(payload))
    loaded = deserialize_dataframe(payload)

    assert table.schema.field("image").metadata is None
    assert loaded["image"].tolist() == df["image"].tolist()


def test_dataframe_round_trip_preserves_mixed_scalars_and_large_integer() -> None:
    values = [b"binary", "text", 2**100, 1.5, None]
    df = pd.DataFrame({"mixed": values}, dtype=object)

    loaded = deserialize_dataframe(serialize_dataframe(df))

    assert loaded["mixed"].tolist() == values


def test_dataframe_round_trip_preserves_mixed_numeric_types() -> None:
    values = [1, 1.5]
    df = pd.DataFrame({"mixed": pd.Series(values, dtype=object)})

    loaded = deserialize_dataframe(serialize_dataframe(df))

    assert loaded["mixed"].tolist() == values
    assert [type(value) for value in loaded["mixed"]] == [int, float]


def test_dataframe_round_trip_preserves_nanosecond_temporal_values() -> None:
    timestamp = pd.Timestamp("2025-01-01 00:00:00.123456789")
    datetime64 = np.datetime64("2025-01-02T00:00:00.987654321", "ns")
    timedelta64 = np.timedelta64(123456789, "ns")
    df = pd.DataFrame(
        {
            "timestamps": pd.Series([timestamp, datetime64, "mixed"], dtype=object),
            "durations": pd.Series([timedelta64, "mixed", None], dtype=object),
        }
    )

    loaded = deserialize_dataframe(serialize_dataframe(df))

    assert loaded["timestamps"].tolist() == [timestamp, pd.Timestamp(datetime64), "mixed"]
    assert all(isinstance(value, pd.Timestamp) for value in loaded["timestamps"][:2])
    assert loaded["durations"].tolist() == [pd.Timedelta(timedelta64), "mixed", None]


def test_dataframe_rejects_invalid_unicode() -> None:
    with pytest.raises(ValueError, match="not valid UTF-8"):
        ExecResult(df=pd.DataFrame({"text": ["bad\ud800text"]}))


def test_dataframe_rejects_invalid_unicode_column_name() -> None:
    with pytest.raises(ValueError, match="column name contains text that is not valid UTF-8"):
        ExecResult(df=pd.DataFrame([[1]], columns=["bad\ud800name"]))


def test_dataframe_rejects_unsupported_fallback_value() -> None:
    class Unsupported:
        pass

    with pytest.raises(ValueError, match="unsupported value type Unsupported"):
        ExecResult(df=pd.DataFrame({"mixed": ["text", Unsupported()]}))


def test_dataframe_deserialize_rejects_unversioned_parquet() -> None:
    output = io.BytesIO()
    pd.DataFrame({"x": [1]}).to_parquet(output)

    with pytest.raises(ValueError, match="unsupported DataFrame format"):
        deserialize_dataframe(output.getvalue())


def test_exec_result_json_round_trip_uses_dataframe_codec() -> None:
    image = {"bytes": b"\x89PNG\r\n\x1a\n", "path": None}
    df = pd.DataFrame(
        {
            "image": [image],
            "value": [Decimal("10.5")],
            "created_at": pd.to_datetime(["2025-01-01"]),
        }
    )
    result = ExecResult(df=df)

    payload = result.model_dump_json()
    loaded = ExecResult.model_validate_json(payload)

    assert '"format":"parquet_v1"' in payload
    assert '"preview"' not in payload
    assert loaded.df is not None
    assert loaded.df.at[0, "image"] == image
    assert loaded.df.at[0, "value"] == Decimal("10.5")


def test_exec_result_rejects_old_dataframe_payload() -> None:
    encoded = base64.b64encode(serialize_dataframe(pd.DataFrame({"x": [1]}))).decode()

    with pytest.raises(ValueError, match="invalid DataFrame payload"):
        ExecResult.model_validate({"df": {"format": "parquet_base64_v1", "parquet_base64": encoded}})
