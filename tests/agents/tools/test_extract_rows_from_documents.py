"""Tests for document extraction into SQL tables."""

from collections.abc import Sequence
from datetime import date
import io
from pathlib import Path
from types import SimpleNamespace

import duckdb
from PIL import Image
import pytest
from pydantic import BaseModel
from pydantic_ai.messages import BinaryContent
from pypdf import PdfWriter

import tabulaflow.agents.tools.extract_rows_from_documents as mod
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector
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
    captured: dict[str, type[BaseModel]] = {}

    class FakeExtractor:
        def __init__(self, **_: object) -> None:
            pass

        async def extract(self, content: str, *, record_type: type[BaseModel], **_: object) -> list[BaseModel]:
            captured["record_type"] = record_type
            return [record_type.model_validate(row) for row in canned]

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
    assert {name: field.annotation for name, field in captured["record_type"].model_fields.items()} == {
        "name": str | None,
        "qty": int | None,
        "price": float | None,
        "active": bool | None,
        "launched": date | None,
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

        async def extract(
            self, content: str | BinaryContent, *, record_type: type[BaseModel], **_: object
        ) -> list[BaseModel]:
            assert isinstance(content, BinaryContent)
            captured.append(content)
            return [record_type.model_validate({"name": "Widget"})]

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
            self, content: str | BinaryContent | Sequence[BinaryContent], *, record_type: type[BaseModel], **_: object
        ) -> list[BaseModel]:
            assert not isinstance(content, (str, BinaryContent))
            captured.append(tuple(content))
            return [record_type.model_validate({"name": "Widget"})]

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
