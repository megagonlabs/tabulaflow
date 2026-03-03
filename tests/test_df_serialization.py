import pandas as pd
from decimal import Decimal
from pandas.testing import assert_frame_equal

from mintq.schema import (
    ExecResult,
    _DF_SERIALIZATION_FORMAT,
    _deserialize_dataframe,
    _serialize_dataframe,
)


def test_dataframe_round_trip_feather_payload() -> None:
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
    assert "feather_base64" in serialized
    assert "preview" in serialized
    assert serialized["preview"]["num_rows"] == 3
    assert len(serialized["preview"]["sample_data"]) == 3

    deserialized = _deserialize_dataframe(serialized)
    assert deserialized is not None
    assert_frame_equal(df, deserialized, check_dtype=True, check_index_type=True)
    assert all(isinstance(v, Decimal) for v in deserialized["amount"])


def test_dataframe_deserialize_legacy_payload() -> None:
    legacy_payload = {
        "schema": {"dtypes": {"x": "int64", "y": "object"}},
        "data": [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}],
    }

    deserialized = _deserialize_dataframe(legacy_payload)
    expected = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
    expected = expected.astype({"x": "int64", "y": "object"})
    assert_frame_equal(expected, deserialized, check_dtype=True)


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

