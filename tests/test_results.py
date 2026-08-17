import math

import pandas as pd
import pytest
from pydantic import ValidationError

from tabulaflow.core import ErrorInfo, ExecResult, GraphResult


@pytest.mark.parametrize(
    "result",
    [
        ExecResult(),
        ExecResult(df=pd.DataFrame({"value": [1]})),
        ExecResult(graph=GraphResult(nodes=[], edges=[])),
        ExecResult(
            df=pd.DataFrame({"value": [1]}),
            graph=GraphResult(nodes=[], edges=[]),
        ),
        ExecResult(affected_rows=0),
        ExecResult(error=ErrorInfo(exc_type="QueryError", message="failed"), latency_seconds=0.1),
    ],
)
def test_accepts_valid_execution_states(result: ExecResult) -> None:
    assert result.succeeded is (result.error is None)


@pytest.mark.parametrize(
    "values",
    [
        {"df": pd.DataFrame(), "error": ErrorInfo(exc_type="QueryError", message="failed")},
        {"graph": GraphResult(nodes=[], edges=[]), "error": ErrorInfo(exc_type="QueryError", message="failed")},
        {"affected_rows": 1, "error": ErrorInfo(exc_type="QueryError", message="failed")},
        {"df": pd.DataFrame(), "affected_rows": 1},
        {"graph": GraphResult(nodes=[], edges=[]), "affected_rows": 1},
    ],
)
def test_rejects_contradictory_execution_states(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ExecResult.model_validate(values)


@pytest.mark.parametrize(
    "values",
    [
        {"affected_rows": -1},
        {"latency_seconds": -0.1},
        {"latency_seconds": math.nan},
        {"latency_seconds": math.inf},
    ],
)
def test_rejects_invalid_numeric_metadata(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ExecResult.model_validate(values)
