"""Shared Playwright browser process and page budget."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Playwright

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class _PageBudget:
    """Process-wide cap on simultaneously-open browser pages.

    A tool's first page may wait for capacity because it holds no permit. Later
    pages fail immediately rather than waiting while holding a permit, which
    prevents deadlock between concurrent multi-page agents.
    """

    def __init__(self, limit: int | None) -> None:
        self._limit = limit
        self._in_use = 0
        self._cond = asyncio.Condition()

    async def acquire(self, *, block: bool) -> bool:
        limit = self._limit
        if limit is None:
            return True
        async with self._cond:
            if self._in_use < limit:
                self._in_use += 1
                return True
            if not block:
                return False
            await self._cond.wait_for(lambda: self._in_use < limit)
            self._in_use += 1
            return True

    async def release(self) -> None:
        if self._limit is None:
            return
        async with self._cond:
            if self._in_use > 0:
                self._in_use -= 1
                self._cond.notify(1)


class WebBrowserManager:
    """Own one Chromium process, shared context, and process-wide page budget.

    The agent runtime owns the default manager. Direct construction is reserved
    for tests and callers that need a separate browser lifecycle.
    """

    def __init__(self, headless: bool = True, max_pages: int | None = None) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._shared_context: BrowserContext | None = None
        self._lock = asyncio.Lock()
        self._page_budget = _PageBudget(max_pages)

    async def acquire_page(self, *, block: bool) -> bool:
        """Acquire a page permit, optionally waiting for capacity."""
        return await self._page_budget.acquire(block=block)

    async def release_page(self) -> None:
        """Release one previously acquired page permit."""
        await self._page_budget.release()

    async def shared_context(self) -> BrowserContext:
        """Return the lazily created process-wide browser context."""
        if self._shared_context is not None:
            return self._shared_context
        async with self._lock:
            if self._shared_context is None:
                browser = await self._ensure_browser_locked()
                self._shared_context = await browser.new_context(
                    user_agent=_USER_AGENT,
                    accept_downloads=False,
                )
            return self._shared_context

    async def new_isolated_context(self) -> BrowserContext:
        """Create a browser context with isolated cookies and storage."""
        async with self._lock:
            browser = await self._ensure_browser_locked()
        return await browser.new_context(
            user_agent=_USER_AGENT,
            accept_downloads=False,
        )

    async def close(self) -> None:
        """Close the context, Chromium process, and Playwright runtime."""
        async with self._lock:
            if self._shared_context is not None:
                try:
                    await self._shared_context.close()
                except Exception:
                    pass
                self._shared_context = None
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None

    async def _ensure_browser_locked(self) -> Browser:
        if self._browser is not None and self._browser.is_connected():
            return self._browser
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError(
                "playwright is not installed. Install with: uv add playwright && uv run playwright install chromium"
            ) from e
        self._playwright = await async_playwright().start()
        try:
            if not Path(self._playwright.chromium.executable_path).is_file():
                raise RuntimeError(
                    "Chromium is not installed. Ask the user to install it, or obtain their permission before "
                    "running an installation command with the shell tool. Run `playwright install chromium` in "
                    "the environment where TabulaFlow is installed. For `uv tool install`, run "
                    "`uv tool run --from playwright playwright install chromium`. After installation, retry the "
                    "browser action; restarting TabulaFlow is not required."
                )
            if not self._headless:
                logger.info("Launching Chromium in headed mode")
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
            return self._browser
        except BaseException:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
            raise
