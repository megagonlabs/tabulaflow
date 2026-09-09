import base64
import io
from typing import Any, cast

import pandas as pd
import numpy as np
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
from tabulaflow.data.registry import DataConnectorRegistry


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
    global_id = "media"
    language = "duckdb"

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
    assert f"[binary: {len(image)} bytes]" in text
    assert f"[binary: {len(document)} bytes]" in text
    assert "(2 media items attached)" in text
    assert returned.content is not None
    content = list(returned.content)
    assert content[0] == "Media #1 from result row 1, column image:"
    assert isinstance(content[1], BinaryContent)
    assert content[1].media_type == "image/png"
    assert content[2] == "Media #2 from result row 1, column document:"
    assert isinstance(content[3], BinaryContent)
    assert content[3].media_type == "application/pdf"


async def test_run_query_attaches_mixed_media_from_one_collection_cell() -> None:
    image = _png()
    document = _pdf()
    media = np.array([image, {"bytes": document, "media_type": "application/pdf"}], dtype=object)
    result = ExecResult(df=pd.DataFrame({"media": [media]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT media", include_media=True
    )

    text = _text(returned)
    assert f"[binary: {len(image)} bytes]" in text
    assert f"[binary: {len(document)} bytes]" in text
    assert "(2 media items attached)" in text
    assert returned.content is not None
    content = list(returned.content)
    assert content[0] == "Media #1 from result row 1, column media[0]:"
    assert isinstance(content[1], BinaryContent) and content[1].media_type == "image/png"
    assert content[2] == "Media #2 from result row 1, column media[1]:"
    assert isinstance(content[3], BinaryContent) and content[3].media_type == "application/pdf"


async def test_run_query_accepts_data_uri_media_without_exposing_base64() -> None:
    image = _png()
    encoded = base64.b64encode(image).decode()
    uri = f"data:image/png;base64,{encoded}"
    result = ExecResult(df=pd.DataFrame({"image": [uri]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image", include_media=True
    )

    assert encoded not in _text(returned)
    assert f"[binary: {len(image)} bytes]" in _text(returned)
    assert "(1 media item attached)" in _text(returned)
    assert returned.content is not None


async def test_run_query_counts_data_uri_padding_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _png()
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", len(image))
    uri = f"data:image/png;base64,{base64.b64encode(image).decode()}"
    result = ExecResult(df=pd.DataFrame({"image": [uri]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image", include_media=True
    )

    assert returned.content is not None
    assert "(1 media item attached)" in _text(returned)


async def test_run_query_preserves_values_for_unsupported_and_invalid_media() -> None:
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
    assert "[binary: 20 bytes]" in text
    assert "'bytes': '[binary: 12 bytes]'" in text
    assert "'bytes': None, 'path': '/tmp/external.png'" in text
    assert "/tmp/image.png" in text
    assert "https://example.com/image.png" in text
    assert "media omitted" not in text
    assert "(0 media items attached; 3 candidates not attached)" in text
    assert "Media attachment issues:" in text
    assert "row 1, column audio: recognized audio/wav is not supported as a model attachment" in text
    assert "it remains available in the result and can be shown as an artifact" in text
    assert "row 1, column invalid: invalid or unsupported image/png" in text
    assert "row 1, column external: path-backed media '/tmp/external.png' has no inline bytes" in text
    assert returned.content is None


async def test_run_query_preserves_paths_while_redacting_nested_bytes() -> None:
    result = ExecResult(
        df=pd.DataFrame(
            {
                "images": [
                    np.array(
                        [
                            {"bytes": None, "path": "first.jpg"},
                            {"bytes": b"not an image", "path": "second.jpg"},
                        ],
                        dtype=object,
                    )
                ]
            }
        )
    )

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT images", include_media=True
    )

    text = _text(returned)
    assert "first.jpg" in text
    assert "second.jpg" in text
    assert "'bytes': None" in text
    assert "[binary: 12 bytes]" in text
    assert "media omitted" not in text
    assert "(0 media items attached; 2 candidates not attached)" in text
    assert "row 1, column images[0]: path-backed media 'first.jpg' has no inline bytes" in text
    assert "row 1, column images[1]: media type could not be determined" in text
    assert returned.content is None


async def test_run_query_enforces_media_item_limit() -> None:
    image = _png()
    result = ExecResult(df=pd.DataFrame({f"image_{index}": [image] for index in range(11)}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT images", include_media=True
    )

    assert returned.content is not None
    assert len(returned.content) == 20
    assert f"[binary: {len(image)} bytes]" in _text(returned)
    assert "media omitted" not in _text(returned)
    assert "(10 media items attached; 1 candidate not attached)" in _text(returned)
    assert "row 1, column image_10: 10-item attachment limit reached" in _text(returned)


async def test_run_query_enforces_normalized_media_total(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _png()
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", len(image))
    result = ExecResult(df=pd.DataFrame({"first": [image], "second": [image]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT images", include_media=True
    )

    assert returned.content is not None
    assert len(returned.content) == 2
    assert f"[binary: {len(image)} bytes]" in _text(returned)
    assert "media omitted" not in _text(returned)
    assert "(1 media item attached; 1 candidate not attached)" in _text(returned)
    assert "total attachment limit reached" in _text(returned)


async def test_run_query_omits_single_value_over_media_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", 4)
    result = ExecResult(df=pd.DataFrame({"blob": [b"12345"]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT blob", include_media=True
    )

    assert "[binary: 5 bytes]" in _text(returned)
    assert "(0 media items attached; 1 candidate not attached)" in _text(returned)
    assert "row 1, column blob: 5 bytes exceeds 4-byte limit" in _text(returned)
    assert returned.content is None


async def test_run_query_does_not_decode_oversized_data_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", 4)

    def fail_decode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("oversized data URI was decoded")

    monkeypatch.setattr("tabulaflow.agents.media.to_binary_content", fail_decode)
    result = ExecResult(df=pd.DataFrame({"image": ["data:image/png;base64,MTIzNDU="]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image", include_media=True
    )

    assert "[binary: 5 bytes]" in _text(returned)
    assert "(0 media items attached; 1 candidate not attached)" in _text(returned)
    assert returned.content is None


async def test_run_query_checks_budget_after_image_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _bmp()
    monkeypatch.setattr(run_query_module, "_MAX_MEDIA_BYTES", len(image) + 1)
    result = ExecResult(df=pd.DataFrame({"image": [image]}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT image", include_media=True
    )

    assert f"[binary: {len(image)} bytes]" in _text(returned)
    assert "(0 media items attached; 1 candidate not attached)" in _text(returned)
    assert "normalized image/png exceeds" in _text(returned)
    assert returned.content is None


async def test_run_query_bounds_media_attachment_issues() -> None:
    result = ExecResult(df=pd.DataFrame({f"blob_{index}": [b"not media"] for index in range(7)}))

    returned = await RunQueryTool(cast(Any, _ResultConnector(result)), enable_media=True)(
        "SELECT * FROM assets", include_media=True
    )

    text = _text(returned)
    assert "(0 media items attached; 7 candidates not attached)" in text
    assert text.count("media type could not be determined") == 5
    assert "- 2 more attachment issues" in text


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
    registry = DataConnectorRegistry()
    registry.register("assets", cast(Any, _ResultConnector(result)))
    tool = RegistryRunQueryTool(registry, enable_media=True)

    returned = await tool("assets", "SELECT image FROM assets", include_media=True)

    assert returned.content is not None
    assert "[source_id=S1]" in _text(returned)
    payload = await tool._output_store.get_result("R1")  # noqa: SLF001
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
