from typing import Any, cast

from PIL import Image
from pydantic_ai import ToolReturn
from pydantic_ai.messages import BinaryContent
import pytest

from tabulaflow.agents.tools.browser.tool import PageSnapshot, _TabState, WebBrowserTool


def _png_bytes() -> bytes:
    import io

    output = io.BytesIO()
    Image.new("RGB", (2, 3), "red").save(output, format="PNG")
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


def _assert_png_result(result: str | ToolReturn) -> None:
    assert isinstance(result, ToolReturn)
    assert result.content is not None
    assert len(result.content) == 1
    image = result.content[0]
    assert isinstance(image, BinaryContent)
    assert image.media_type == "image/png"


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

    _assert_png_result(viewport)
    _assert_png_result(element)
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

    _assert_png_result(result)
    assert isinstance(result, ToolReturn)
    assert isinstance(result.return_value, str)
    assert "Image: https://example.com/image.png" in result.return_value
    assert state.last_snapshot is not None
    assert state.last_snapshot.refs == []


def test_browser_registers_screenshot_tool() -> None:
    names = [tool.name for tool in WebBrowserTool().as_pydantic_ai_tools()]

    assert "browser_screenshot" in names
