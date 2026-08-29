"""Tests for type-aware row extraction in ``ExtractRowsFromDocumentsTool``.

The output schema is typed per the target column: the LLM emits a native
``int``/``float``/``bool`` (or ``null``) instead of a string the database would have
to coerce on INSERT — an unparseable string would otherwise abort the whole batch
append. These tests cover the type resolution and wiring without invoking an LLM.
"""

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest
from pydantic_ai.settings import ModelSettings

import tabulaflow.agents.tools.extract_rows_from_documents as mod
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector
from tabulaflow.agents.extraction import EntityExtractor
from tabulaflow.agents.extraction.column_types import python_type_for_dtype
from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool


def test_python_type_for_dtype() -> None:
    """Numeric/boolean/temporal canonical tokens map to native types; everything else to ``str``."""
    # Canonical SQLAlchemy visit-names the schema actually records (DuckDB workspace),
    # plus raw-SQL fallbacks. BIG_INTEGER/SMALL_INTEGER are what BIGINT/SMALLINT columns
    # introspect to — they must not fall through to str.
    for tok in ("TINY_INTEGER", "SMALL_INTEGER", "INTEGER", "BIG_INTEGER", "TINYINT", "SMALLINT", "INT", "BIGINT"):
        assert python_type_for_dtype(tok) is int, tok
    for tok in ("FLOAT", "DOUBLE", "NUMERIC", "DECIMAL", "REAL", "DOUBLE_PRECISION"):
        assert python_type_for_dtype(tok) is float, tok
    assert python_type_for_dtype("BOOLEAN") is bool
    assert python_type_for_dtype("DATE") is date
    # All TIMESTAMP variants (and DATETIME) flatten to a naive datetime.
    for tok in ("DATETIME", "TIMESTAMP", "TIMESTAMPTZ", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ"):
        assert python_type_for_dtype(tok) is datetime
    # Text, TIME, and semi-structured types all fall through to str.
    for tok in ("VARCHAR", "TEXT", "TIME", "JSON", "ARRAY", "STRUCT", "UUID", "BINARY"):
        assert python_type_for_dtype(tok) is str


def test_entity_extractor_builds_typed_model() -> None:
    """Per-column types produce a nullable, JSON-typed structured-output model."""
    ex = EntityExtractor(
        ["name", "qty", "price", "active", "day", "at"],
        column_types={"qty": int, "price": float, "active": bool, "day": date, "at": datetime},
    )
    entity_model = ex._result_model.model_fields["entities"].annotation.__args__[0]  # type: ignore[union-attr]
    props = entity_model.model_json_schema()["properties"]

    def json_types(col: str) -> set[str | None]:
        spec = props[col]
        return {s.get("type") for s in spec.get("anyOf", [spec])}

    def json_formats(col: str) -> set[str | None]:
        spec = props[col]
        return {s.get("format") for s in spec.get("anyOf", [spec])}

    assert json_types("name") == {"string", "null"}
    assert json_types("qty") == {"integer", "null"}
    assert json_types("price") == {"number", "null"}
    assert json_types("active") == {"boolean", "null"}
    # date/datetime serialize as ISO strings carrying a format hint for the LLM.
    assert json_types("day") == {"string", "null"} and "date" in json_formats("day")
    assert json_types("at") == {"string", "null"} and "date-time" in json_formats("at")


def test_entity_extractor_rebuilds_agent_when_profile_changes() -> None:
    settings = ModelSettings(temperature=0)
    ex = EntityExtractor(["name"])
    original_agent = ex._agent

    ex.apply_llm_profile(llm="openai-responses:gpt-5", model_settings=settings)

    assert ex.llm == "openai-responses:gpt-5"
    assert ex.model_settings is settings
    assert ex._agent is not original_agent


def test_typed_model_coerces_and_nulls() -> None:
    """Pydantic coerces strings to typed values, accepts null, and rejects junk (no silent pass)."""
    ex = EntityExtractor(
        ["qty", "price", "active", "day"],
        column_types={"qty": int, "price": float, "active": bool, "day": date},
    )
    entity_model = ex._result_model.model_fields["entities"].annotation.__args__[0]  # type: ignore[union-attr]

    coerced = entity_model(qty="5", price="29.99", active="true", day="2024-01-02")
    assert (coerced.qty, coerced.price, coerced.active, coerced.day) == (5, 29.99, True, date(2024, 1, 2))

    nulled = entity_model(qty=None, price=None, active=None, day=None)
    assert (nulled.qty, nulled.price, nulled.active, nulled.day) == (None, None, None, None)

    with pytest.raises(ValueError):
        entity_model(qty="N/A")
    with pytest.raises(ValueError):
        entity_model(day="not a date")


def test_entity_extractor_rejects_unsupported_column_type() -> None:
    """Only str/int/float/bool/date/datetime are accepted; anything else fails fast."""
    from decimal import Decimal

    with pytest.raises(ValueError, match="str/int/float/bool/date/datetime"):
        EntityExtractor(["amt"], column_types={"amt": Decimal})  # type: ignore[dict-item]


async def test_tool_resolves_types_and_appends_typed_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool resolves output-column types from the schema and appends native values.

    The LLM is stubbed; the test exercises type resolution, extractor wiring, the
    DataFrame build, and the DuckDB append — including a ``None`` landing as SQL NULL
    in numeric columns.
    """
    db_path = str(tmp_path / "products.duckdb")
    raw = duckdb.connect(db_path)
    raw.execute("CREATE TABLE products (name VARCHAR, qty INTEGER, price DOUBLE, active BOOLEAN, launched DATE)")
    raw.close()

    conn = await SQLConnector.from_url_async(
        global_id="test+extract_rows",
        url=f"duckdb:///{db_path}",
        db_name="products",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )
    conn.read_only = False

    canned: list[dict[str, object]] = [
        {"name": "Widget", "qty": 5, "price": 29.99, "active": True, "launched": "2024-01-01"},
        {"name": "Gadget", "qty": None, "price": None, "active": False, "launched": "2023-06-15"},
    ]
    captured: dict[str, dict[str, type]] = {}

    class FakeExtractor:
        def __init__(
            self, output_columns: list[str], *, column_types: dict[str, type] | None = None, **_: object
        ) -> None:
            captured["column_types"] = column_types or {}

        async def extract(self, content: str, **_: object) -> list[dict[str, object]]:
            return canned

    monkeypatch.setattr(mod, "EntityExtractor", FakeExtractor)

    tool = ExtractRowsFromDocumentsTool(conn)
    summary = await tool.execute(
        None,
        "products",
        task_query="SELECT 'irrelevant doc text' AS content",
        task_instruction="Extract each product.",
        output_columns=["name", "qty", "price", "active", "launched"],
        tool_call_id="call-1",
    )

    assert "Extracted 2 entities" in summary
    assert captured["column_types"] == {
        "name": str,
        "qty": int,
        "price": float,
        "active": bool,
        "launched": date,
    }

    back = (await conn.run_query_async("SELECT * FROM products ORDER BY name")).df
    assert back is not None
    gadget, widget = back.iloc[0], back.iloc[1]
    assert widget["name"] == "Widget" and int(widget["qty"]) == 5 and float(widget["price"]) == 29.99
    assert bool(widget["active"]) is True and str(widget["launched"])[:10] == "2024-01-01"
    # The missing numerics land as SQL NULL rather than a batch-aborting junk string.
    assert gadget["name"] == "Gadget"
    assert back["qty"].isna().sum() == 1 and back["price"].isna().sum() == 1


async def test_tool_rejects_non_scalar_output_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-scalar (array/json/...) output column is rejected up front, not stringified."""
    db_path = str(tmp_path / "docs.duckdb")
    raw = duckdb.connect(db_path)
    raw.execute("CREATE TABLE docs (title VARCHAR, tags VARCHAR[])")
    raw.close()

    conn = await SQLConnector.from_url_async(
        global_id="test+extract_rows_reject",
        url=f"duckdb:///{db_path}",
        db_name="docs",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )
    conn.read_only = False

    def _boom(*_: object, **__: object) -> object:
        raise AssertionError("extraction must not run when an output column is non-scalar")

    monkeypatch.setattr(mod, "EntityExtractor", _boom)

    summary = await ExtractRowsFromDocumentsTool(conn)(
        SimpleNamespace(tool_call_id="call-1"),  # type: ignore[arg-type]
        None,
        "docs",
        task_query="SELECT 'doc' AS content",
        task_instruction="Extract each tag.",
        output_columns=["title", "tags"],
    )
    assert "non-scalar" in summary and "tags" in summary and "ARRAY" in summary


async def test_unknown_placeholder_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A task_instruction placeholder that is not a task_query column is rejected up front."""
    db_path = str(tmp_path / "docs.duckdb")
    raw = duckdb.connect(db_path)
    raw.execute("CREATE TABLE docs (title VARCHAR)")
    raw.close()

    conn = await SQLConnector.from_url_async(
        global_id="test+extract_rows_placeholder",
        url=f"duckdb:///{db_path}",
        db_name="docs",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )
    conn.read_only = False

    def _boom(*_: object, **__: object) -> object:
        raise AssertionError("extraction must not run on a placeholder mismatch")

    monkeypatch.setattr(mod, "EntityExtractor", _boom)

    summary = await ExtractRowsFromDocumentsTool(conn)(
        SimpleNamespace(tool_call_id="call-1"),  # type: ignore[arg-type]
        None,
        "docs",
        # task_query projects 'url'; the instruction references a typo 'urll'.
        task_query="SELECT body AS content, url FROM (VALUES ('doc', 'u')) AS v(body, url)",
        task_instruction="Extract from {{ urll }}.",
        output_columns=["title"],
    )
    assert summary.startswith("(error:") and "not in the task_query result" in summary
