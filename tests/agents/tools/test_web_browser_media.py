import io
from typing import Any, cast

from PIL import Image
from pydantic_ai import ToolReturn
from pydantic_ai.messages import BinaryContent
import pytest
from pypdf import PdfWriter

from tabulaflow.agents.tools.browser.tool import PageSnapshot, _TabState, WebBrowserTool


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 3), "red").save(output, format="PNG")
    return output.getvalue()


def _pdf_bytes(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=200)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class _FakeLocator:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def screenshot(self, *, type: str) -> bytes:
        assert type == "png"
        return self._data


class _FakePage:
    url = "https://example.com/chart"

    def __init__(self, data: bytes) -> None:
        self._data = data

    async def screenshot(self, *, type: str) -> bytes:
        assert type == "png"
        return self._data

    def locator(self, selector: str) -> _FakeLocator:
        assert selector == "aria-ref=e1"
        return _FakeLocator(self._data)


class _FakeResponse:
    def __init__(self, data: bytes, media_type: str = "image/png") -> None:
        self._data = data
        self.headers = {"content-type": media_type}

    async def body(self) -> bytes:
        return self._data


def _assert_media_result(result: str | ToolReturn, media_type: str) -> BinaryContent:
    assert isinstance(result, ToolReturn)
    assert result.content is not None
    assert len(result.content) == 1
    content = result.content[0]
    assert isinstance(content, BinaryContent)
    assert content.media_type == media_type
    return content


async def test_browser_screenshot_captures_viewport_and_ref() -> None:
    data = _png_bytes()
    page = _FakePage(data)
    state = _TabState(
        tab_id="t1",
        page=cast(Any, page),
        last_touched_turn=0,
        last_snapshot=PageSnapshot(url=page.url, title="Chart", refs=["e1"]),
    )
    browser = WebBrowserTool()
    browser._tabs[state.tab_id] = state

    viewport = await browser.browser_screenshot("t1")
    element = await browser.browser_screenshot("t1", "e1")

    _assert_media_result(viewport, "image/png")
    _assert_media_result(element, "image/png")
    assert isinstance(viewport, ToolReturn)
    assert isinstance(viewport.return_value, str)
    assert "Screenshot: current viewport" in viewport.return_value
    assert isinstance(element, ToolReturn)
    assert isinstance(element.return_value, str)
    assert "Screenshot: element e1" in element.return_value
    assert browser.metrics().num_screenshots == 2


async def test_browser_screenshot_rejects_unknown_ref() -> None:
    page = _FakePage(_png_bytes())
    state = _TabState(
        tab_id="t1",
        page=cast(Any, page),
        last_touched_turn=0,
        last_snapshot=PageSnapshot(url=page.url, title="Chart", refs=[]),
    )
    browser = WebBrowserTool()
    browser._tabs[state.tab_id] = state

    result = await browser.browser_screenshot("t1", "e1")

    assert isinstance(result, str)
    assert "unknown ref 'e1'" in result


async def test_browser_navigate_returns_direct_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _png_bytes()
    page = _FakePage(data)
    state = _TabState(tab_id="t1", page=cast(Any, page), last_touched_turn=0)
    response = _FakeResponse(data, media_type="image/jpeg")
    browser = WebBrowserTool()

    async def open_new_tab() -> tuple[_TabState, None]:
        browser._tabs[state.tab_id] = state
        return state, None

    async def goto(_page: object, _url: str) -> _FakeResponse:
        return response

    monkeypatch.setattr(browser, "_open_new_tab", open_new_tab)
    monkeypatch.setattr(browser, "_goto", goto)

    result = await browser.browser_navigate("https://example.com/image.png")

    _assert_media_result(result, "image/png")
    assert isinstance(result, ToolReturn)
    assert isinstance(result.return_value, str)
    assert "Image: https://example.com/image.png" in result.return_value
    assert state.last_snapshot is not None
    assert state.last_snapshot.refs == []


async def test_browser_returns_native_pdf() -> None:
    page = _FakePage(_png_bytes())
    state = _TabState(tab_id="t1", page=cast(Any, page), last_touched_turn=0)
    browser = WebBrowserTool()

    result = await browser._render_pdf_bytes(
        state,
        "https://example.com/report.pdf",
        _pdf_bytes(3),
        "application/pdf",
    )

    _assert_media_result(result, "application/pdf")
    assert isinstance(result, ToolReturn)
    assert isinstance(result.return_value, str)
    assert "PDF: https://example.com/report.pdf (3 pages" in result.return_value
    assert state.last_snapshot is not None
    assert state.last_snapshot.refs == []


def test_browser_registers_screenshot_tool() -> None:
    names = [tool.name for tool in WebBrowserTool().as_pydantic_ai_tools()]

    assert "browser_screenshot" in names
