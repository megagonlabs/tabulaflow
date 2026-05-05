"""Stateful browser tool with per-agent isolation.

Singleton browser process + per-agent BrowserContext (default shared, optionally
isolated) + one Page per tool instance. Five LLM-facing actions each return a
filtered list of clickable elements + clean markdown content of the post-action
page state.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Literal
from urllib.parse import urlparse

from pydantic import BaseModel
from pydantic_ai import Tool

if TYPE_CHECKING:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Locator,
        Page,
        Playwright,
    )

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NAV_TIMEOUT_MS = 30_000
_SETTLE_TIMEOUT_MS = 10_000
_MAX_MARKDOWN_CHARS = 30_000
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_REF_PATTERN = re.compile(r"\[ref=(e\d+)\]")

# Aria snapshot line: optional indent, "- role", optional `"name"`, `[ref=eN]`,
# optional trailing attrs and colon. Captures: role, name, ref.
_ARIA_LINE_PATTERN = re.compile(
    r'^(?P<indent>\s*)-\s+(?P<role>[\w-]+)(?:\s+"(?P<name>[^"]*)")?'
    r'.*?\[ref=(?P<ref>e\d+)\].*?$'
)
_ARIA_URL_PATTERN = re.compile(r"^\s*-\s+/url:\s*(?P<url>.+?)\s*$")

_INTERACTIVE_ROLES: frozenset[str] = frozenset(
    {
        "button",
        "link",
        "textbox",
        "combobox",
        "checkbox",
        "radio",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "tab",
        "switch",
        "slider",
        "spinbutton",
        "searchbox",
        "option",
    }
)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class WebBrowserToolMetrics(BaseModel):
    num_navigates: int = 0
    num_clicks: int = 0
    num_types: int = 0
    num_scrolls: int = 0
    num_backs: int = 0
    num_errors: int = 0
    num_popups_adopted: int = 0


# ---------------------------------------------------------------------------
# Snapshot: interactive elements + clean markdown
#
# Two complementary views of the page:
#   1. Filtered list of interactive elements (with refs for click/type)
#   2. Clean markdown content of the page (for reading)
#
# Refs come from Playwright's ``aria_snapshot(mode="ai")`` and resolve via the
# ``aria-ref=eN`` locator. Markdown comes from lxml-cleaned ``page.content()``
# run through markdownify (matches browser-use / OpenHands' approach).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InteractiveElement:
    ref: str
    role: str
    name: str
    href: str | None = None


@dataclass
class PageSnapshot:
    url: str
    title: str
    interactive_elements: list[InteractiveElement] = field(default_factory=list)
    markdown_content: str = ""
    refs: set[str] = field(default_factory=set)


def parse_interactive_elements(aria_yaml: str) -> list[InteractiveElement]:
    """Extract interactive elements from an aria-snapshot YAML string.

    Walks the YAML line-by-line. For each interactive role, captures ref +
    name; for links, also peeks at following indented lines for ``/url:``.
    """
    lines = aria_yaml.split("\n")
    elements: list[InteractiveElement] = []
    for i, line in enumerate(lines):
        m = _ARIA_LINE_PATTERN.match(line)
        if m is None:
            continue
        role = m.group("role")
        if role not in _INTERACTIVE_ROLES:
            continue
        name = m.group("name") or ""
        ref = m.group("ref")
        href: str | None = None
        if role == "link":
            # Look ahead within the link's indented block for `- /url:`
            indent_level = len(m.group("indent"))
            for next_line in lines[i + 1 : i + 6]:
                if not next_line.strip():
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent_level:
                    break
                um = _ARIA_URL_PATTERN.match(next_line)
                if um is not None:
                    href = um.group("url")
                    break
        elements.append(InteractiveElement(ref=ref, role=role, name=name, href=href))
    return elements


def render_interactive_elements(elements: list[InteractiveElement]) -> str:
    """Render a flat list of interactive elements for the LLM."""
    if not elements:
        return "(no interactive elements)"
    out: list[str] = []
    for e in elements:
        line = f"- [ref={e.ref}] {e.role}"
        if e.name:
            line += f' "{e.name}"'
        if e.href:
            line += f" → {e.href}"
        out.append(line)
    return "\n".join(out)


async def _annotate_dom_with_refs(page: "Page", refs: set[str]) -> None:
    """Inject ``data-ref`` attributes onto interactive DOM nodes.

    Uses Playwright's ``aria-ref`` locator to find each AX node's underlying
    DOM element and sets ``data-ref="eN"``. Subsequent HTML extraction
    preserves the attribute through ``lxml.Cleaner``; the markdown converter
    reads it to embed refs at element positions.

    Per-element ``evaluate`` calls run in parallel. Failures (stale refs,
    detached nodes, navigations mid-flight) are silently skipped.
    """
    if not refs:
        return

    async def _set_one(ref: str) -> None:
        try:
            await page.locator(f"aria-ref={ref}").evaluate(
                "(el, refValue) => el.setAttribute('data-ref', refValue)",
                ref,
                timeout=1000,
            )
        except Exception:
            pass

    await asyncio.gather(*(_set_one(r) for r in refs))


def _build_ref_preserving_converter() -> "object":
    """Build a markdownify converter subclass that emits ``[ref=eN]`` after
    interactive elements with a ``data-ref`` attribute.

    Imported lazily so we tolerate markdownify being unavailable.
    """
    from markdownify import MarkdownConverter

    class RefPreservingConverter(MarkdownConverter):  # type: ignore[misc, valid-type]
        @staticmethod
        def _ref_suffix(el: object) -> str:
            ref = el.get("data-ref")  # type: ignore[attr-defined]
            return f" [ref={ref}]" if ref else ""

        def convert_a(self, el, text, *args, **kwargs):  # type: ignore[no-untyped-def]
            out = super().convert_a(el, text, *args, **kwargs)
            return out + self._ref_suffix(el)

        def convert_button(self, el, text, *args, **kwargs):  # type: ignore[no-untyped-def]
            ref = self._ref_suffix(el)
            text_clean = (text or "").strip()
            if not text_clean and not ref:
                return ""
            return f"**{text_clean or 'button'}**{ref} "

        def convert_input(self, el, text, *args, **kwargs):  # type: ignore[no-untyped-def]
            ref = self._ref_suffix(el)
            if not ref:
                return ""
            input_type = (el.get("type") or "text").lower()
            if input_type in ("text", "email", "password", "search", "tel", "url", "number"):
                label = el.get("placeholder") or el.get("aria-label") or "input"
                value = el.get("value") or ""
                inner = f'value="{value}"' if value else f'placeholder="{label}"'
                return f"[textbox {inner}{ref}] "
            if input_type in ("checkbox", "radio"):
                checked = "✓ " if el.get("checked") is not None else ""
                label = el.get("aria-label") or ""
                name = (label + " ").strip()
                return f"[{input_type} {checked}{name}{ref}] "
            if input_type in ("submit", "button"):
                return f"**{el.get('value') or input_type}**{ref} "
            return ""

        def convert_textarea(self, el, text, *args, **kwargs):  # type: ignore[no-untyped-def]
            ref = self._ref_suffix(el)
            if not ref:
                return ""
            label = el.get("placeholder") or el.get("aria-label") or "textarea"
            return f"[textarea {label}{ref}] "

        def convert_select(self, el, text, *args, **kwargs):  # type: ignore[no-untyped-def]
            ref = self._ref_suffix(el)
            if not ref:
                return ""
            label = el.get("aria-label") or "combobox"
            return f"[combobox {label}{ref}] "

    return RefPreservingConverter


_INLINE_TAGS: frozenset[str] = frozenset(
    {
        "span", "em", "i", "strong", "b", "u", "s", "small",
        "sub", "sup", "mark", "cite", "q", "time", "abbr",
        "code", "var", "samp", "kbd",
    }
)


def _prune_hidden_duplicates(doc: object) -> None:
    """Remove subtrees that contain no ``data-ref`` descendants.

    aria_snapshot's mode='ai' filters hidden content from Chromium's
    accessibility tree, so visible elements get ``data-ref`` attrs (via
    ``_annotate_dom_with_refs``). Hidden duplicates (e.g., tab content
    rendered redundantly in the DOM, mobile/desktop variant menus, SEO
    duplicates) have no ``data-ref`` and would otherwise leak into markdown
    via the raw HTML path.

    Algorithm: bottom-up mark elements whose subtree contains a ``data-ref``,
    then remove unmarked elements at the boundary. For inline formatting
    elements (em, strong, span, etc.) being removed, their text content is
    preserved by merging into surrounding text — so a paragraph with a
    ``data-ref`` doesn't lose ``<em>important</em>`` when em itself has no
    ref of its own.
    """
    # Mark elements whose subtree contains a data-ref (bottom-up).
    for el in reversed(list(doc.iter())):  # type: ignore[attr-defined]
        if el.get("data-ref"):
            el.set("_kr", "1")
        else:
            for child in el:
                if child.get("_kr") == "1":
                    el.set("_kr", "1")
                    break
    # Collect boundary elements (unmarked, parent marked).
    to_remove = []
    for el in doc.iter():  # type: ignore[attr-defined]
        if el.tag in ("html", "body", "head"):
            continue
        if el.get("_kr") == "1":
            continue
        parent = el.getparent()
        if parent is None or parent.get("_kr") == "1":
            to_remove.append(el)
    # Remove. For inline elements, preserve text content to avoid losing
    # mid-paragraph emphasis/formatting.
    for el in to_remove:
        parent = el.getparent()
        if parent is None:
            continue
        prev = el.getprevious()
        # Preserve inner text only for inline elements.
        if el.tag in _INLINE_TAGS:
            inner_text = "".join(el.itertext())
            if inner_text:
                if prev is not None:
                    prev.tail = (prev.tail or "") + inner_text
                else:
                    parent.text = (parent.text or "") + inner_text
        # Always preserve trailing text (whitespace, punctuation).
        if el.tail:
            if prev is not None:
                prev.tail = (prev.tail or "") + el.tail
            else:
                parent.text = (parent.text or "") + el.tail
        parent.remove(el)
    # Cleanup the marker attribute so it doesn't leak into output.
    for el in doc.iter():  # type: ignore[attr-defined]
        if "_kr" in el.attrib:
            del el.attrib["_kr"]


async def extract_markdown(page: "Page", refs: set[str]) -> str:
    """Extract clean markdown from the live rendered page with refs inlined.

    Pipeline: annotate DOM with ``data-ref`` attrs → page.content() →
    lxml.Cleaner (strips scripts/styles/nav/footer) → prune subtrees with
    no refs (drops hidden duplicates) → custom markdownify converter that
    emits ``[ref=eN]`` after interactive elements.
    """
    await _annotate_dom_with_refs(page, refs)

    try:
        html = await page.content()
    except Exception as e:
        return f"(error fetching HTML: {e})"

    try:
        import lxml.html
        from lxml.html.clean import Cleaner

        doc = lxml.html.fromstring(html)
        cleaner = Cleaner(
            scripts=True,
            style=True,
            page_structure=False,
            embedded=True,
            forms=False,
            frames=True,
            javascript=True,
            meta=True,
            links=False,
            processing_instructions=True,
            safe_attrs_only=False,  # preserve data-ref attrs we injected
            kill_tags=[
                "nav",
                "footer",
                "header",
                "svg",
                "iframe",
                "noscript",
                "aside",
            ],
        )
        doc = cleaner.clean_html(doc)
        _prune_hidden_duplicates(doc)
        main_candidates = (
            doc.xpath("//main")
            or doc.xpath("//article")
            or [doc.body if doc.body is not None else doc]
        )
        cleaned_html = lxml.html.tostring(main_candidates[0], encoding="unicode")
    except Exception as e:
        logger.debug("lxml cleanup failed: %s; falling back to raw HTML", e)
        cleaned_html = html

    try:
        converter_cls = _build_ref_preserving_converter()
    except ImportError:
        return "(error: markdownify is not installed)"

    converter = converter_cls(
        heading_style="ATX",
        strip=["script", "style", "img"],
        bullets="-",
        escape_asterisks=False,
        escape_underscores=False,
        escape_misc=False,
        autolinks=False,
        default_title=False,
    )
    md = converter.convert(cleaned_html)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()

    if len(md) > _MAX_MARKDOWN_CHARS:
        truncate_at = _MAX_MARKDOWN_CHARS
        para_break = md.rfind("\n\n", _MAX_MARKDOWN_CHARS - 500, _MAX_MARKDOWN_CHARS)
        if para_break > 0:
            truncate_at = para_break
        md = (
            md[:truncate_at]
            + f"\n\n[content truncated at {truncate_at} of {len(md)} chars]"
        )
    return md


async def take_snapshot(page: "Page") -> PageSnapshot:
    """Capture the current page as a filtered interactive view + markdown."""
    try:
        aria_yaml = await page.aria_snapshot(mode="ai", timeout=_SETTLE_TIMEOUT_MS)
    except Exception as e:
        aria_yaml = ""
        logger.debug("aria_snapshot failed: %s", e)
    interactive = parse_interactive_elements(aria_yaml)
    refs = set(_REF_PATTERN.findall(aria_yaml))
    markdown = await extract_markdown(page, refs)
    title = ""
    try:
        title = await page.title()
    except Exception:
        pass
    return PageSnapshot(
        url=page.url,
        title=title,
        interactive_elements=interactive,
        markdown_content=markdown,
        refs=refs,
    )


# ---------------------------------------------------------------------------
# Browser process manager (singleton)
# ---------------------------------------------------------------------------


class WebBrowserManager:
    """Process-wide singleton: one Chromium, one shared BrowserContext.

    Use ``await WebBrowserManager.get()`` to access. Subsequent callers
    receive the same instance; cold-start launch is serialized by the
    ``_launch_lock``.
    """

    _instance: ClassVar["WebBrowserManager | None"] = None
    _instance_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._shared_context: BrowserContext | None = None
        self._launch_lock = asyncio.Lock()

    @classmethod
    async def get(cls) -> "WebBrowserManager":
        async with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def shared_context(self) -> "BrowserContext":
        """Return the shared BrowserContext, launching the browser if needed."""
        if self._shared_context is not None:
            return self._shared_context
        async with self._launch_lock:
            if self._shared_context is not None:
                return self._shared_context
            browser = await self._ensure_browser_locked()
            self._shared_context = await browser.new_context(
                user_agent=_USER_AGENT,
                accept_downloads=False,
            )
            return self._shared_context

    async def new_isolated_context(self) -> "BrowserContext":
        """Create a fresh private BrowserContext for tools that need isolation."""
        async with self._launch_lock:
            browser = await self._ensure_browser_locked()
        return await browser.new_context(
            user_agent=_USER_AGENT,
            accept_downloads=False,
        )

    async def close(self) -> None:
        """Tear down the shared context, browser, and Playwright runtime."""
        async with self._launch_lock:
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

    @classmethod
    async def reset(cls) -> None:
        """Close and discard the singleton. Mainly useful for tests."""
        async with cls._instance_lock:
            if cls._instance is not None:
                await cls._instance.close()
                cls._instance = None

    # internals ---------------------------------------------------------------

    async def _ensure_browser_locked(self) -> "Browser":
        """Launch Chromium if not already running. Caller must hold ``_launch_lock``."""
        if self._browser is not None and self._browser.is_connected():
            return self._browser
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError(
                "playwright is not installed. Install with: "
                "uv add playwright && uv run playwright install chromium"
            ) from e
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser


# ---------------------------------------------------------------------------
# Internal exceptions
# ---------------------------------------------------------------------------


class _RefError(Exception):
    """Raised when a snapshot ref cannot be resolved."""


# ---------------------------------------------------------------------------
# Per-agent tool
# ---------------------------------------------------------------------------


class WebBrowserTool:
    """Per-agent stateful browser tool.

    One instance owns one Page in either the shared or a private
    BrowserContext. Exposes 5 LLM-facing actions; each returns the
    post-action page snapshot.
    """

    name: ClassVar = "web_browser"

    def __init__(
        self,
        manager: WebBrowserManager | None = None,
        isolated: bool = False,
    ) -> None:
        """Initialize the tool.

        Args:
            manager: BrowserManager instance to use. If None, the
                process-wide singleton is used (recommended).
            isolated: If True, this tool gets its own private
                BrowserContext instead of sharing the manager's default
                context. Use when an agent needs cookie/storage isolation
                from peers.
        """
        self._manager = manager
        self._isolated = isolated
        self._owned_context: BrowserContext | None = None
        self._page: Page | None = None
        self._op_lock = asyncio.Lock()
        self._last_snapshot: PageSnapshot | None = None
        self._popup_notice: str | None = None
        self._metrics = WebBrowserToolMetrics()

    # === LLM-facing tool methods ============================================

    async def browser_navigate(self, url: str) -> str:
        """Navigate to a URL and return the post-load page state.

        The page is rendered with a headless browser and the response is an
        aria snapshot of the page. Interactive elements are tagged with
        ``[ref=eN]`` markers; pass those refs to ``browser_click`` and
        ``browser_type``.

        Args:
            url: An ``http://`` or ``https://`` URL.
        """
        self._metrics.num_navigates += 1
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return self._format_error(
                f"unsupported URL scheme {parsed.scheme!r}; only http/https allowed"
            )
        if not parsed.netloc:
            return self._format_error("invalid URL — missing host")

        async with self._op_lock:
            try:
                page = await self._ensure_page()
                await page.goto(url, wait_until="networkidle", timeout=_NAV_TIMEOUT_MS)
            except Exception as e:
                return self._format_error(f"navigation failed: {self._error_message(e)}")
            return await self._format_response()

    async def browser_click(self, ref: str) -> str:
        """Click an interactive element by its ref id from the latest snapshot.

        Args:
            ref: The ref string from the latest snapshot's ``[ref=eN]`` markers.
        """
        self._metrics.num_clicks += 1
        async with self._op_lock:
            if self._page is None:
                return self._format_error("no page; call browser_navigate first")
            try:
                locator = self._resolve_ref(ref)
                await locator.click(timeout=_SETTLE_TIMEOUT_MS)
                await self._settle_after_action()
            except _RefError as e:
                return self._format_error(str(e))
            except Exception as e:
                return self._format_error(f"click failed: {self._error_message(e)}")
            return await self._format_response()

    async def browser_type(self, ref: str, text: str, submit: bool = False) -> str:
        """Type text into an editable element.

        Args:
            ref: The ref string of the input element.
            text: The text to type. Replaces existing content in the field.
            submit: If True, press Enter after typing (useful for search boxes).
        """
        self._metrics.num_types += 1
        async with self._op_lock:
            if self._page is None:
                return self._format_error("no page; call browser_navigate first")
            try:
                locator = self._resolve_ref(ref)
                await locator.fill(text, timeout=_SETTLE_TIMEOUT_MS)
                if submit:
                    await locator.press("Enter")
                    await self._settle_after_action()
            except _RefError as e:
                return self._format_error(str(e))
            except Exception as e:
                return self._format_error(f"type failed: {self._error_message(e)}")
            return await self._format_response()

    async def browser_scroll(
        self, direction: Literal["up", "down", "top", "bottom"]
    ) -> str:
        """Scroll the page.

        Args:
            direction: One of ``"up"``, ``"down"``, ``"top"``, ``"bottom"``.
                ``"down"``/``"up"`` move by ~80% of the viewport height;
                ``"top"``/``"bottom"`` jump to the start/end of the page
                (useful for triggering infinite-scroll loaders).
        """
        self._metrics.num_scrolls += 1
        if direction not in ("up", "down", "top", "bottom"):
            return self._format_error(
                f"invalid direction {direction!r}; expected up/down/top/bottom"
            )
        async with self._op_lock:
            if self._page is None:
                return self._format_error("no page; call browser_navigate first")
            try:
                if direction == "down":
                    await self._page.evaluate(
                        "window.scrollBy(0, window.innerHeight * 0.8)"
                    )
                elif direction == "up":
                    await self._page.evaluate(
                        "window.scrollBy(0, -window.innerHeight * 0.8)"
                    )
                elif direction == "top":
                    await self._page.evaluate("window.scrollTo(0, 0)")
                else:  # bottom
                    await self._page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                await asyncio.sleep(0.5)  # let lazy-loaded content settle
            except Exception as e:
                return self._format_error(f"scroll failed: {self._error_message(e)}")
            return await self._format_response()

    async def browser_back(self) -> str:
        """Navigate back in browser history."""
        self._metrics.num_backs += 1
        async with self._op_lock:
            if self._page is None:
                return self._format_error("no page; call browser_navigate first")
            try:
                await self._page.go_back(
                    wait_until="networkidle", timeout=_NAV_TIMEOUT_MS
                )
            except Exception as e:
                return self._format_error(f"back failed: {self._error_message(e)}")
            return await self._format_response()

    # === Lifecycle ===========================================================

    async def close(self) -> None:
        """Close this tool's page and (if isolated) its private context."""
        async with self._op_lock:
            if self._page is not None:
                try:
                    await self._page.close()
                except Exception:
                    pass
                self._page = None
            if self._owned_context is not None:
                try:
                    await self._owned_context.close()
                except Exception:
                    pass
                self._owned_context = None

    # === Pydantic-AI integration =============================================

    def as_pydantic_ai_tools(self) -> list[Tool]:
        return [
            Tool(self.browser_navigate, name="browser_navigate"),
            Tool(self.browser_click, name="browser_click"),
            Tool(self.browser_type, name="browser_type"),
            Tool(self.browser_scroll, name="browser_scroll"),
            Tool(self.browser_back, name="browser_back"),
        ]

    def metrics(self) -> WebBrowserToolMetrics:
        return self._metrics

    # === Internals ===========================================================

    async def _ensure_manager(self) -> WebBrowserManager:
        if self._manager is None:
            self._manager = await WebBrowserManager.get()
        return self._manager

    async def _ensure_page(self) -> "Page":
        if self._page is not None:
            return self._page
        manager = await self._ensure_manager()
        if self._isolated:
            self._owned_context = await manager.new_isolated_context()
            ctx = self._owned_context
        else:
            ctx = await manager.shared_context()
        page = await ctx.new_page()
        page.on("popup", self._on_popup_sync)
        self._page = page
        return page

    def _on_popup_sync(self, popup: "Page") -> None:
        """Sync wrapper that schedules the async popup adoption."""
        asyncio.create_task(self._on_popup(popup))

    async def _on_popup(self, popup: "Page") -> None:
        """Adopt a site-popped tab as the new active page."""
        try:
            await popup.wait_for_load_state("domcontentloaded", timeout=_SETTLE_TIMEOUT_MS)
        except Exception:
            pass
        old_page = self._page
        self._page = popup
        try:
            popup_url = popup.url
        except Exception:
            popup_url = "(unknown)"
        self._popup_notice = (
            f"[note: previous action opened a popup; the active tab is now {popup_url}]"
        )
        self._metrics.num_popups_adopted += 1
        if old_page is not None and old_page is not popup:
            try:
                await old_page.close()
            except Exception:
                pass
        popup.on("popup", self._on_popup_sync)

    async def _settle_after_action(self) -> None:
        """After an action that may navigate or load content, wait briefly."""
        if self._page is None:
            return
        try:
            await self._page.wait_for_load_state("networkidle", timeout=_SETTLE_TIMEOUT_MS)
        except Exception:
            pass

    def _resolve_ref(self, ref: str) -> "Locator":
        if self._last_snapshot is None:
            raise _RefError("no snapshot available; call any action first to refresh")
        if ref not in self._last_snapshot.refs:
            available = sorted(self._last_snapshot.refs)
            raise _RefError(f"unknown ref {ref!r}. Available refs: {available[:30]}")
        if self._page is None:
            raise _RefError("no active page")
        return self._page.locator(f"aria-ref={ref}")

    async def _format_response(self) -> str:
        page = self._page
        assert page is not None
        snapshot = await take_snapshot(page)
        self._last_snapshot = snapshot

        # Refs that landed in the markdown are inlined where the element is.
        # Refs that didn't (chrome stripped by lxml.Cleaner, etc.) get
        # listed below for completeness.
        inlined = set(_REF_PATTERN.findall(snapshot.markdown_content))
        remaining = [
            e for e in snapshot.interactive_elements if e.ref not in inlined
        ]

        parts: list[str] = []
        if self._popup_notice is not None:
            parts.append(self._popup_notice)
            parts.append("")
            self._popup_notice = None
        parts.append(f"URL: {snapshot.url}")
        if snapshot.title:
            parts.append(f"Title: {snapshot.title}")
        parts.append("")
        parts.append("# Page")
        parts.append(snapshot.markdown_content or "(no content extracted)")
        if remaining:
            parts.append("")
            parts.append("# Other interactive elements")
            parts.append(render_interactive_elements(remaining))
        return "\n".join(parts)

    def _format_error(self, msg: str) -> str:
        self._metrics.num_errors += 1
        return f"(error: {msg})"

    @staticmethod
    def _error_message(e: Exception) -> str:
        msg = str(e).strip()
        return msg or e.__class__.__name__
