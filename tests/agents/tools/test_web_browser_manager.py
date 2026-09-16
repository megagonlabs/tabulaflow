from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tabulaflow.agents.tools.browser.manager import WebBrowserManager


def _mock_playwright(monkeypatch: pytest.MonkeyPatch, fake_playwright: Any) -> None:
    from playwright import async_api

    starter = SimpleNamespace(start=AsyncMock(return_value=fake_playwright))
    monkeypatch.setattr(async_api, "async_playwright", lambda: starter)


async def test_missing_chromium_has_actionable_error_and_stops_playwright(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chromium = SimpleNamespace(
        executable_path=str(tmp_path / "missing-chromium"),
        launch=AsyncMock(),
    )
    playwright = SimpleNamespace(chromium=chromium, stop=AsyncMock())
    _mock_playwright(monkeypatch, playwright)
    manager = WebBrowserManager()

    with pytest.raises(RuntimeError, match="uv tool run --from playwright playwright install chromium"):
        await manager.shared_context()

    chromium.launch.assert_not_awaited()
    playwright.stop.assert_awaited_once()
    assert manager._playwright is None


async def test_browser_launch_failure_stops_playwright(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "chromium"
    executable.touch()
    launch_error = RuntimeError("launch failed")
    chromium = SimpleNamespace(
        executable_path=str(executable),
        launch=AsyncMock(side_effect=launch_error),
    )
    playwright = SimpleNamespace(chromium=chromium, stop=AsyncMock())
    _mock_playwright(monkeypatch, playwright)
    manager = WebBrowserManager()

    with pytest.raises(RuntimeError, match="launch failed") as exc_info:
        await manager.shared_context()

    assert exc_info.value is launch_error
    playwright.stop.assert_awaited_once()
    assert manager._playwright is None
