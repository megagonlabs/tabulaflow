"""Fetch a URL with a headless Chromium and return markdown content.

Uses Playwright to render JavaScript and trafilatura to extract the main
content as markdown. The browser is launched lazily on first use and reused
across calls; each call gets a fresh BrowserContext so cookies and storage
don't leak between fetches.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlparse

from pydantic import BaseModel
from pydantic_ai import Tool

if TYPE_CHECKING:
    from playwright.async_api import Browser, Playwright

logger = logging.getLogger(__name__)

_TIMEOUT_MS = 30_000
_MAX_OUTPUT_CHARS = 30_000
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class WebFetchToolMetrics(BaseModel):
    num_calls: int = 0
    num_errors: int = 0
    num_timeouts: int = 0


class WebFetchTool:
    """Fetch a URL with headless Chromium and return extracted markdown."""

    name: ClassVar = "web_fetch"

    def __init__(
        self,
        timeout_ms: int = _TIMEOUT_MS,
        max_output_chars: int = _MAX_OUTPUT_CHARS,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._max_output_chars = max_output_chars
        self._metrics = WebFetchToolMetrics()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> "Browser":
        if self._browser is not None and self._browser.is_connected():
            return self._browser
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError(
                "playwright is not installed. Install with: "
                "uv add playwright trafilatura && uv run playwright install chromium"
            ) from e
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    def _truncate(self, text: str) -> str:
        if len(text) <= self._max_output_chars:
            return text
        half = self._max_output_chars // 2
        return text[:half] + f"\n\n... (output truncated: {len(text)} chars total) ...\n\n" + text[-half:]

    async def __call__(self, url: str) -> str:
        """Fetch a URL and return its main content as markdown.

        The page is rendered with a headless browser, so JavaScript-driven
        content (SPAs, dynamic dashboards) is included. Boilerplate such as
        navigation, footers, and sidebars is stripped.

        Args:
            url: An ``http://`` or ``https://`` URL to fetch.
        """
        self._metrics.num_calls += 1

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            self._metrics.num_errors += 1
            return f"(error: unsupported URL scheme {parsed.scheme!r}; only http/https allowed)"
        if not parsed.netloc:
            self._metrics.num_errors += 1
            return "(error: invalid URL — missing host)"

        try:
            import trafilatura
        except ImportError:
            self._metrics.num_errors += 1
            return "(error: trafilatura is not installed. Install with: uv add trafilatura)"

        try:
            from playwright.async_api import Error as PlaywrightError
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        except ImportError:
            self._metrics.num_errors += 1
            return (
                "(error: playwright is not installed. Install with: "
                "uv add playwright && uv run playwright install chromium)"
            )

        async with self._lock:
            try:
                browser = await self._ensure_browser()
            except Exception as e:
                self._metrics.num_errors += 1
                return f"(error: failed to launch browser: {e})"

        context = None
        try:
            context = await browser.new_context(
                user_agent=_USER_AGENT,
                accept_downloads=False,
            )
            page = await context.new_page()
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=self._timeout_ms)
            except PlaywrightTimeoutError:
                self._metrics.num_timeouts += 1
                return f"(error: navigation timed out after {self._timeout_ms // 1000}s)"
            except PlaywrightError as e:
                self._metrics.num_errors += 1
                return f"(error: navigation failed: {e.message})"

            status = response.status if response is not None else None
            html = await page.content()
        except Exception as e:
            self._metrics.num_errors += 1
            return f"(error: failed to fetch page: {e})"
        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

        markdown = trafilatura.extract(
            html,
            output_format="markdown",
            include_links=True,
            include_tables=True,
            include_formatting=True,
            with_metadata=True,
        )
        if not markdown:
            self._metrics.num_errors += 1
            preface = f"(warning: no main content extracted; HTTP {status})\n" if status else ""
            return preface + "(error: page produced no extractable content)"

        header = f"[{status} {url}]\n\n" if status is not None else f"[{url}]\n\n"
        return header + self._truncate(markdown)

    async def close(self) -> None:
        """Shut down the browser and Playwright runtime."""
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

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> WebFetchToolMetrics:
        return self._metrics
