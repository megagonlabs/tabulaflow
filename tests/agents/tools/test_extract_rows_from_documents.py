"""Tests for type-aware row extraction in ``ExtractRowsFromDocumentsTool``.

The output schema is typed per the target column: the LLM emits a native
``int``/``float``/``bool`` (or ``null``) instead of a string the database would have
to coerce on INSERT — an unparseable string would otherwise abort the whole batch
append. These tests cover the type resolution and wiring without invoking an LLM.
"""

from datetime import date, datetime
import io
from pathlib import Path
from types import SimpleNamespace
from collections.abc import Sequence
from typing import Any

import duckdb
from PIL import Image
import pytest
from pydantic_ai.messages import BinaryContent, UserContent
from pydantic_ai.settings import ModelSettings
from pypdf import PdfWriter

import tabulaflow.agents.tools.extract_rows_from_documents as mod
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector
from tabulaflow.agents.extraction import EntityExtractor
from tabulaflow.agents.extraction.column_types import python_type_for_dtype
from tabulaflow.agents.media import select_pdf_pages
from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1, 1), "red").save(output, format="PNG")
    return output.getvalue()


def _pdf(pages: int) -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=10, height=10)
    writer.write(output)
    return output.getvalue()


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
        llm="test",
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


def test_entity_extractor_rebuilds_agent_when_profile_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789ab4x")
    settings = ModelSettings(temperature=0)
    ex = EntityExtractor(["name"], llm="test")
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
        llm="test",
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


def test_document_content_validation_rejects_unknown_values_and_accepts_null() -> None:
    assert mod._prepare_document_content(1, None) is None  # noqa: SLF001
    with pytest.raises(TypeError, match="unsupported content in row 2"):
        mod._prepare_document_content(2, {"unexpected": "value"})  # noqa: SLF001


@pytest.mark.parametrize(
    "value, location",
    [
        ({"bytes": None, "path": "one.jpg"}, "row 1"),
        ([{"bytes": None, "path": "one.jpg"}, {"bytes": None, "path": "two.jpg"}], "row 1, item 0"),
    ],
)
def test_document_content_rejects_path_backed_media_with_guidance(value: object, location: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        mod._prepare_document_content(1, value)  # noqa: SLF001

    message = str(exc_info.value)
    assert location in message
    assert "path-backed media 'one.jpg' has no inline bytes" in message
    assert "download the referenced file and import its bytes" in message


async def test_entity_extractor_splits_pdfs_into_page_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    extractor = EntityExtractor(["name"], llm="test")
    prompts: list[list[UserContent]] = []

    async def capture(prompt: str | Sequence[UserContent], _trajectory: str) -> list[dict[str, Any]]:
        assert not isinstance(prompt, str)
        prompts.append(list(prompt))
        return []

    monkeypatch.setattr(extractor, "_extract_chunk", capture)

    await extractor.extract(
        BinaryContent(data=_pdf(41), media_type="application/pdf"),
        instruction="Extract every name.",
    )

    assert len(prompts) == 3
    media = [prompt[1] for prompt in prompts]
    assert all(isinstance(item, BinaryContent) for item in media)
    assert [select_pdf_pages(item.data).total_pages for item in media if isinstance(item, BinaryContent)] == [20, 20, 1]
    assert "PDF pages 1-20 of 41" in str(prompts[0][0])
    assert "PDF pages 41-41 of 41" in str(prompts[2][0])


async def test_entity_extractor_processes_ordered_mixed_media_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = EntityExtractor(["name"], llm="test")
    prompts: list[list[UserContent]] = []

    async def capture(prompt: str | Sequence[UserContent], _trajectory: str) -> list[dict[str, Any]]:
        assert not isinstance(prompt, str)
        prompts.append(list(prompt))
        return []

    monkeypatch.setattr(extractor, "_extract_chunk", capture)

    await extractor.extract(
        [
            BinaryContent(data=_png(), media_type="image/png"),
            BinaryContent(data=_pdf(1), media_type="application/pdf"),
        ],
        instruction="Extract every name.",
    )

    assert len(prompts) == 2
    assert "Media item 1 of 2" in str(prompts[0][0])
    assert "Media item 2 of 2" in str(prompts[1][0])
    assert [prompt[1].media_type for prompt in prompts if isinstance(prompt[1], BinaryContent)] == [
        "image/png",
        "application/pdf",
    ]


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
        display_name="products",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
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


async def test_tool_extracts_rows_from_inline_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "images.duckdb")
    raw = duckdb.connect(db_path)
    raw.execute("CREATE TABLE source (content BLOB)")
    raw.execute("INSERT INTO source VALUES (?)", [_png()])
    raw.execute("CREATE TABLE products (name VARCHAR)")
    raw.close()

    conn = await SQLConnector.from_url_async(
        global_id="test+extract_image_rows",
        url=f"duckdb:///{db_path}",
        display_name="images",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    conn.read_only = False
    captured: list[BinaryContent] = []

    class FakeExtractor:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def extract(self, content: str | BinaryContent, **_: object) -> list[dict[str, object]]:
            assert isinstance(content, BinaryContent)
            captured.append(content)
            return [{"name": "Widget"}]

    monkeypatch.setattr(mod, "EntityExtractor", FakeExtractor)

    summary = await ExtractRowsFromDocumentsTool(conn).execute(
        None,
        "products",
        task_query="SELECT content FROM source",
        task_instruction="Extract every product.",
        output_columns=["name"],
    )

    assert "Extracted 1 entities" in summary
    assert len(captured) == 1 and captured[0].media_type == "image/png"
    assert (await conn.run_query_async("SELECT name FROM products")).df.iloc[0, 0] == "Widget"  # type: ignore[union-attr]


async def test_tool_extracts_from_mixed_media_collection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "mixed-media.duckdb")
    raw = duckdb.connect(db_path)
    raw.execute("CREATE TABLE source (content BLOB[])")
    raw.execute("INSERT INTO source VALUES (?)", [[_png(), _pdf(1)]])
    raw.execute("CREATE TABLE products (name VARCHAR)")
    raw.close()

    conn = await SQLConnector.from_url_async(
        global_id="test+extract_mixed_media_rows",
        url=f"duckdb:///{db_path}",
        display_name="mixed_media",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    conn.read_only = False
    captured: list[tuple[BinaryContent, ...]] = []

    class FakeExtractor:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def extract(
            self, content: str | BinaryContent | Sequence[BinaryContent], **_: object
        ) -> list[dict[str, object]]:
            assert not isinstance(content, (str, BinaryContent))
            captured.append(tuple(content))
            return [{"name": "Widget"}]

    monkeypatch.setattr(mod, "EntityExtractor", FakeExtractor)

    summary = await ExtractRowsFromDocumentsTool(conn).execute(
        None,
        "products",
        task_query="SELECT content FROM source",
        task_instruction="Extract every product.",
        output_columns=["name"],
    )

    assert "Extracted 1 entities" in summary
    assert [item.media_type for item in captured[0]] == ["image/png", "application/pdf"]


async def test_tool_rejects_unknown_binary_before_extraction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "unknown-binary.duckdb")
    raw = duckdb.connect(db_path)
    raw.execute("CREATE TABLE source (content BLOB)")
    raw.execute("INSERT INTO source VALUES ('not media'::BLOB)")
    raw.execute("CREATE TABLE products (name VARCHAR)")
    raw.close()

    conn = await SQLConnector.from_url_async(
        global_id="test+extract_unknown_binary",
        url=f"duckdb:///{db_path}",
        display_name="unknown_binary",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    conn.read_only = False

    def fail(*_: object, **__: object) -> object:
        raise AssertionError("extractor should not be constructed")

    monkeypatch.setattr(mod, "EntityExtractor", fail)
    summary = await ExtractRowsFromDocumentsTool(conn)(
        SimpleNamespace(tool_call_id="call-1"),  # type: ignore[arg-type]
        None,
        "products",
        task_query="SELECT content FROM source",
        task_instruction="Extract every product.",
        output_columns=["name"],
    )

    assert summary.startswith("(error:")
    assert "unusable content in row 1" in summary


async def test_tool_rejects_non_scalar_output_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-scalar (array/json/...) output column is rejected up front, not stringified."""
    db_path = str(tmp_path / "docs.duckdb")
    raw = duckdb.connect(db_path)
    raw.execute("CREATE TABLE docs (title VARCHAR, tags VARCHAR[])")
    raw.close()

    conn = await SQLConnector.from_url_async(
        global_id="test+extract_rows_reject",
        url=f"duckdb:///{db_path}",
        display_name="docs",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
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
        display_name="docs",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
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
