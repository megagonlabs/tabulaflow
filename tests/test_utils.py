from decimal import Decimal
import json
import math

import numpy as np
import pandas as pd
import pytest

from tabulaflow.core.serialization import dumps_strict_json, json_ready
from tabulaflow.agents.response_parsing import extract_code


@pytest.mark.asyncio
async def test_extract_code() -> None:
    responses = [
        "SELECT * FROM users",
        "```\nSELECT * FROM users\n```",
        "```python\nSELECT * FROM users\n```",
        "```sql\nSELECT * FROM users\n```",
        "```sql\nSELECT * FROM users\n```\n",
        "```\nSELECT * FROM users\n```",
        "```\n\nSELECT * FROM users\n```",
        "This is the SQL code:\n```sql\nSELECT * FROM users\n```",
        "This is the SQL code:\n```sql\nSELECT * FROM users\n```. This is another SQL code:\n```sql\nSELECT * FROM products\n```",
    ]
    for response in responses:
        code = extract_code(response)
        assert code == "SELECT * FROM users"


def test_json_ready_normalizes_missing_and_non_finite_values() -> None:
    payload = {
        "python_nan": math.nan,
        "python_inf": math.inf,
        "pandas_na": pd.NA,
        "pandas_nat": pd.NaT,
        "numpy_nat": np.datetime64("NaT"),
        "decimal_nan": Decimal("NaN"),
        "decimal_inf": Decimal("Infinity"),
        "nested": [np.float64("nan"), {"x": (1, np.float64("inf"))}],
    }

    assert json_ready(payload) == {
        "python_nan": None,
        "python_inf": None,
        "pandas_na": None,
        "pandas_nat": None,
        "numpy_nat": None,
        "decimal_nan": None,
        "decimal_inf": None,
        "nested": [None, {"x": [1, None]}],
    }


def test_json_ready_recurses_through_data_shaped_containers() -> None:
    payload = {"tuple": (1, Decimal("2.5"), pd.NA), "list": [np.float64("inf")]}

    assert json_ready(payload) == {"tuple": [1, "2.5", None], "list": [None]}


def test_json_ready_stringifies_unsupported_values() -> None:
    assert json_ready(b"data") == "b'data'"


def test_dumps_strict_json_rejects_non_json_constants_after_normalization() -> None:
    text = dumps_strict_json({"values": [math.nan, np.float64("inf"), Decimal("NaN")]})

    assert "NaN" not in text
    assert "Infinity" not in text
    assert json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token))) == {
        "values": [None, None, None]
    }
