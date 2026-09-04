import base64
import io
from typing import Any, ClassVar, Literal, cast

import pandas as pd
from PIL import Image
import pytest
from pydantic_ai import Agent, ToolReturn
from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pypdf import PdfWriter

import tabulaflow.agents.tools.run_query as run_query_module
from tabulaflow.agents.tools.registry.run_query import RegistryRunQueryTool
from tabulaflow.agents.tools.run_query import RunQueryTool
from tabulaflow.core import ExecResult
from tabulaflow.data.registry import DBRegistry


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1, 1), "red").save(output, format="PNG")
    return output.getvalue()


def _bmp() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1, 1), "red").save(output, format="BMP")
    return output.getvalue()


def _pdf() -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=10, height=10)
    writer.write(output)
    return output.getvalue()


class _ResultConnector:
    connector_type: ClassVar[Literal["sql"]] = "sql"
    global_id = "media"

    def __init__(self, result: ExecResult) -> None:
        self.result = result

    async def run_query_async(self, query: Any, parameters: Any = (), timeout: int | None = None) -> ExecResult:
        return self.result

    async def refresh_schema_async(self) -> None:
        pass


def _text(result: ToolReturn) -> str:
    assert isinstance(result.return_value, str)
    return result.return_value


async def test_run_query_sanitizes_binary_cells_by_default() -> None:
    payload = b"secret payload"
    result = ExecResult(df=pd.DataFrame({"id": [1], "blob": [payload]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)))("SELECT id, blob FROM assets")

    text = _text(returned)
    assert "secret payload" not in text
    assert f"[binary: {len(payload)} bytes]" in text
    assert returned.content is None
    assert result.df is not None
    assert result.df.at[0, "blob"] == payload


async def test_run_query_does_not_attach_media_when_disabled() -> None:
    image = _png()
    result = ExecResult(df=pd.DataFrame({"image": [image]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)))("SELECT image", include_media=True)

    assert f"[binary: {len(image)} bytes]" in _text(returned)
    assert returned.content is None


async def test_run_query_attaches_images_and_pdfs_in_cell_order() -> None:
    image = _png()
    document = _pdf()
    result = ExecResult(
        df=pd.DataFrame(
            {
                "image": [{"bytes": image, "media_type": "application/pdf"}],
                "document": [document],
            }
        )
    )

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image, document", include_media=True
    )

    text = _text(returned)
    assert "[Media #1: image/png" in text
    assert "[Media #2: application/pdf" in text
    assert returned.content is not None
    content = list(returned.content)
    assert content[0] == "Media #1 from result row 1, column image:"
    assert isinstance(content[1], BinaryContent)
    assert content[1].media_type == "image/png"
    assert content[2] == "Media #2 from result row 1, column document:"
    assert isinstance(content[3], BinaryContent)
    assert content[3].media_type == "application/pdf"


async def test_run_query_accepts_data_uri_media_without_exposing_base64() -> None:
    image = _png()
    encoded = base64.b64encode(image).decode()
    uri = f"data:image/png;base64,{encoded}"
    result = ExecResult(df=pd.DataFrame({"image": [uri]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image", include_media=True
    )

    assert encoded not in _text(returned)
    assert "[Media #1: image/png" in _text(returned)
    assert returned.content is not None


async def test_run_query_omits_unsupported_and_invalid_media() -> None:
    result = ExecResult(
        df=pd.DataFrame(
            {
                "audio": [b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 8],
                "invalid": [{"bytes": b"not an image", "media_type": "image/png"}],
                "external": [{"bytes": None, "path": "/tmp/external.png"}],
                "path": ["/tmp/image.png"],
                "url": ["https://example.com/image.png"],
            }
        )
    )

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT * FROM assets", include_media=True
    )

    text = _text(returned)
    assert "[media omitted: unsupported audio/wav]" in text
    assert "[media omitted: invalid image/png]" in text
    assert "[media omitted: invalid or unavailable inline bytes]" in text
    assert "/tmp/image.png" in text
    assert "https://example.com/image.png" in text
    assert returned.content is None


async def test_run_query_enforces_media_item_limit() -> None:
    image = _png()
    result = ExecResult(df=pd.DataFrame({f"image_{index}": [image] for index in range(11)}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT images", include_media=True
    )

    assert returned.content is not None
    assert len(returned.content) == 20
    assert "[media omitted: 10-item limit reached]" in _text(returned)


async def test_run_query_enforces_normalized_media_total(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _png()
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", len(image))
    result = ExecResult(df=pd.DataFrame({"first": [image], "second": [image]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT images", include_media=True
    )

    assert returned.content is not None
    assert len(returned.content) == 2
    assert f"[media omitted: {len(image)}-byte total limit reached]" in _text(returned)


async def test_run_query_omits_single_value_over_media_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", 4)
    result = ExecResult(df=pd.DataFrame({"blob": [b"12345"]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT blob", include_media=True
    )

    assert "[media omitted: 5 bytes exceeds 4-byte limit]" in _text(returned)
    assert returned.content is None


async def test_run_query_does_not_decode_oversized_data_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", 4)

    def fail_decode(_value: object) -> None:
        raise AssertionError("oversized data URI was decoded")

    monkeypatch.setattr(run_query_module, "extract_media_bytes", fail_decode)
    result = ExecResult(df=pd.DataFrame({"image": ["data:image/png;base64,MTIzNDU="]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image", include_media=True
    )

    assert "exceeds 4-byte limit" in _text(returned)
    assert returned.content is None


async def test_run_query_checks_budget_after_image_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _bmp()
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", len(image) + 1)
    result = ExecResult(df=pd.DataFrame({"image": [image]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image", include_media=True
    )

    assert "[media omitted: normalized image/bmp exceeds" in _text(returned)
    assert returned.content is None


async def test_run_query_allows_many_rows_without_media() -> None:
    result = ExecResult(df=pd.DataFrame({"value": range(100)}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT value FROM assets", include_media=True
    )

    text = _text(returned)
    assert "(100 rows)" in text
    assert returned.content is None


async def test_registry_run_query_propagates_media_and_stores_original_result() -> None:
    image = _png()
    result = ExecResult(df=pd.DataFrame({"image": [image]}))
    registry = DBRegistry()
    registry.register("assets", cast(Any, _ResultConnector(result)))
    tool = RegistryRunQueryTool(registry, enable_media=True)

    returned = await tool("assets", "SELECT image FROM assets", include_media=True)

    assert returned.content is not None
    assert "[source_id=S1]" in _text(returned)
    payload = await tool._output_store.get_payload("R1")  # noqa: SLF001
    assert payload.df is not None
    assert payload.df.at[0, "image"] == image


async def test_run_query_media_reaches_model_history() -> None:
    image = _png()
    connector = cast(Any, _ResultConnector(ExecResult(df=pd.DataFrame({"image": [image]}))))
    calls = 0

    def model(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[ToolCallPart(tool_name="run_query", args={"query": "SELECT image", "include_media": True})]
            )
        media = [
            item
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart) and isinstance(part.content, (list, tuple))
            for item in part.content
            if isinstance(item, BinaryContent)
        ]
        assert len(media) == 1
        assert media[0].media_type == "image/png"
        return ModelResponse(parts=[TextPart("done")])

    agent = Agent(
        FunctionModel(model),
        tools=[RunQueryTool(connector, enable_media=True).as_pydantic_ai_tool()],
    )

    result = await agent.run("inspect the image")

    assert result.output == "done"
