"""Concurrent multi-agent, multi-page browser tool built on Playwright.

Designed for fleets of agents browsing in parallel within one Python
process: many agents share one Chromium (not one each), each can open
many pages simultaneously (not one foreground at a time), and idle
pages auto-close between turns (no manual cleanup).  The browser-use
alternative — Chromium-per-session, single foreground page — costs
~15 GB at 50 agents and forces every multi-source workflow through
subagent fan-out.

What this module adds on top of Playwright (and differs from browser-use)
=========================================================================

**One Chromium, many isolated agents.**  Singleton ``WebBrowserManager``
owns one Chromium + a shared ``BrowserContext``; many ``WebBrowserTool``
instances coexist in-process.  ``isolated=True`` opts into a private
context when cookie/storage isolation matters.  Browser-use launches one
Chromium per session — at 50 agents that's 50 browsers vs one here.

**Multi-page state per tool.**  Each tool tracks ``dict[int, Page]``;
``browser_navigate`` opens a *new* page each call, addressed by
``page=N`` in subsequent actions.  Lets the LLM fan out several
parallel ``browser_navigate`` calls in one turn (search-and-explore),
then drill in next turn.  Browser-use's session is single-page;
multi-page there means subagent fan-out (N LLM loops).

**Turn-based auto-cleanup.**  Pages auto-close at the next turn if not
interacted with.  ``lifecycle_capability()`` returns a pydantic-ai
``Hooks`` capability that fires ``tick()`` on ``before_model_request``;
``tick()`` increments the turn counter and closes idle pages.  No
``browser_close`` exposed — the agent declares interest by interaction.

**Markdown with click affordances inline.**  Each tool response is one
document: page text rendered as markdown with ``[ref=eN]`` markers
placed right after each link, button, or input.  The agent reads
``[Subscribe](url) [ref=e15]`` mid-paragraph and clicks ref ``e15`` —
no jumping between a "what's clickable" list and a "what does the page
say" view.  Browser-use exposes those as two separate channels (state
list + ``extract`` markdown).
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
    num_lists: int = 0
    num_errors: int = 0
    num_popups_adopted: int = 0
    num_pages_auto_closed: int = 0


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

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._shared_context: BrowserContext | None = None
        self._launch_lock = asyncio.Lock()

    @classmethod
    async def get(cls, headless: bool = True) -> "WebBrowserManager":
        """Return the process-wide singleton.

        ``headless`` is honored only on first construction; subsequent calls
        return the existing instance regardless of the value passed.
        """
        async with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(headless=headless)
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
        if not self._headless:
            logger.info("Launching Chromium in headed mode")
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        return self._browser


# ---------------------------------------------------------------------------
# Internal exceptions
# ---------------------------------------------------------------------------


class _RefError(Exception):
    """Raised when a snapshot ref cannot be resolved."""


# ---------------------------------------------------------------------------
# Per-page state
# ---------------------------------------------------------------------------


@dataclass
class _PageState:
    """Per-page state held by a multi-page WebBrowserTool."""

    page_id: int
    page: "Page"
    last_touched_turn: int
    last_snapshot: PageSnapshot | None = None
    popup_notice: str | None = None
    op_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


# ---------------------------------------------------------------------------
# Per-agent tool
# ---------------------------------------------------------------------------


class WebBrowserTool:
    """Per-agent stateful browser tool with multi-page support.

    One instance can manage many Pages within a shared (or private)
    BrowserContext. Each ``browser_navigate`` call opens a NEW page; the
    LLM addresses subsequent actions via ``page=N`` to refer back. Pages
    auto-close if the agent doesn't interact with them on the next turn
    (turn boundary detected via a pydantic-ai ``before_model_request`` hook
    — register it by calling ``tool.lifecycle_capability()`` and passing
    the result to ``Agent(capabilities=[...])``).
    """

    name: ClassVar = "web_browser"

    def __init__(
        self,
        manager: WebBrowserManager | None = None,
        isolated: bool = False,
        max_pages: int = 10,
        headless: bool = True,
    ) -> None:
        """Initialize the tool.

        Args:
            manager: BrowserManager instance to use. If None, the
                process-wide singleton is used (recommended).
            isolated: If True, this tool gets its own private
                BrowserContext instead of sharing the manager's default
                context. Use when an agent needs cookie/storage isolation
                from peers.
            max_pages: Cap on simultaneously-open pages for this tool.
                Returns an error if exceeded; idle pages auto-close at
                the next turn boundary.
            headless: Run Chromium headless. Set False for visible-window
                debugging. Honored only on first manager construction;
                subsequent tools share the existing browser regardless.
        """
        self._manager = manager
        self._isolated = isolated
        self._max_pages = max_pages
        self._headless = headless
        self._owned_context: BrowserContext | None = None
        self._pages: dict[int, _PageState] = {}
        self._next_page_id = 1
        self._turn_counter = 0
        self._metrics = WebBrowserToolMetrics()

    # === LLM-facing tool methods ============================================

    async def browser_navigate(self, url: str) -> str:
        """Open a NEW page at ``url`` and return its post-load snapshot.

        Each call opens a fresh page — previously-opened pages remain open.
        Use the ``page`` id from the response in subsequent action calls
        (``browser_click``, etc.) to interact with this page. Pages
        auto-close if not interacted with on the next agent turn.

        Issue multiple navigates in parallel within one turn to scan
        several URLs concurrently.

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
        if len(self._pages) >= self._max_pages:
            return self._format_error(
                f"max_pages ({self._max_pages}) reached. "
                f"Open pages: {sorted(self._pages.keys())}. "
                f"Idle pages auto-close at the next turn boundary."
            )

        page_id = self._next_page_id
        self._next_page_id += 1

        try:
            ctx = await self._ensure_context()
            page = await ctx.new_page()
        except Exception as e:
            return self._format_error(f"failed to open page: {self._error_message(e)}")

        page.on("popup", lambda p, pid=page_id: self._on_popup_sync(pid, p))

        try:
            await page.goto(url, wait_until="networkidle", timeout=_NAV_TIMEOUT_MS)
        except Exception as e:
            try:
                await page.close()
            except Exception:
                pass
            return self._format_error(f"navigation failed: {self._error_message(e)}")

        state = _PageState(page_id=page_id, page=page, last_touched_turn=self._turn_counter)
        self._pages[page_id] = state
        return await self._format_response_for(state)

    async def browser_click(self, page: int, ref: str) -> str:
        """Click an interactive element on a specific page.

        Args:
            page: The id of the page to act on (from a previous response).
            ref: The ref string from that page's latest snapshot.
        """
        self._metrics.num_clicks += 1
        state = self._pages.get(page)
        if state is None:
            return self._format_error(self._unknown_page(page))
        async with state.op_lock:
            try:
                locator = self._resolve_ref(state, ref)
                await locator.click(timeout=_SETTLE_TIMEOUT_MS)
                await self._settle(state)
            except _RefError as e:
                return self._format_error(str(e))
            except Exception as e:
                return self._format_error(f"click failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await self._format_response_for(state)

    async def browser_type(self, page: int, ref: str, text: str, submit: bool = False) -> str:
        """Type text into an editable element on a specific page.

        Args:
            page: The id of the page to act on.
            ref: The ref string of the input element.
            text: The text to type. Replaces existing content.
            submit: If True, press Enter after typing.
        """
        self._metrics.num_types += 1
        state = self._pages.get(page)
        if state is None:
            return self._format_error(self._unknown_page(page))
        async with state.op_lock:
            try:
                locator = self._resolve_ref(state, ref)
                await locator.fill(text, timeout=_SETTLE_TIMEOUT_MS)
                if submit:
                    await locator.press("Enter")
                    await self._settle(state)
            except _RefError as e:
                return self._format_error(str(e))
            except Exception as e:
                return self._format_error(f"type failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await self._format_response_for(state)

    async def browser_scroll(
        self, page: int, direction: Literal["up", "down", "top", "bottom"]
    ) -> str:
        """Scroll a specific page.

        Args:
            page: The id of the page to scroll.
            direction: One of ``"up"``, ``"down"``, ``"top"``, ``"bottom"``.
        """
        self._metrics.num_scrolls += 1
        if direction not in ("up", "down", "top", "bottom"):
            return self._format_error(
                f"invalid direction {direction!r}; expected up/down/top/bottom"
            )
        state = self._pages.get(page)
        if state is None:
            return self._format_error(self._unknown_page(page))
        async with state.op_lock:
            try:
                if direction == "down":
                    await state.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                elif direction == "up":
                    await state.page.evaluate("window.scrollBy(0, -window.innerHeight * 0.8)")
                elif direction == "top":
                    await state.page.evaluate("window.scrollTo(0, 0)")
                else:
                    await state.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.5)
            except Exception as e:
                return self._format_error(f"scroll failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await self._format_response_for(state)

    async def browser_back(self, page: int) -> str:
        """Navigate back in a specific page's history.

        Args:
            page: The id of the page to navigate back on.
        """
        self._metrics.num_backs += 1
        state = self._pages.get(page)
        if state is None:
            return self._format_error(self._unknown_page(page))
        async with state.op_lock:
            try:
                await state.page.go_back(wait_until="networkidle", timeout=_NAV_TIMEOUT_MS)
            except Exception as e:
                return self._format_error(f"back failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await self._format_response_for(state)

    async def browser_list_pages(self) -> str:
        """List currently-open pages with their URLs and titles."""
        self._metrics.num_lists += 1
        if not self._pages:
            return "(no pages open)"
        lines = ["Open pages:"]
        for pid in sorted(self._pages.keys()):
            state = self._pages[pid]
            url = state.page.url
            title = state.last_snapshot.title if state.last_snapshot else ""
            suffix = f" — {title}" if title else ""
            lines.append(f"  page={pid}: {url}{suffix}")
        return "\n".join(lines)

    # === Lifecycle ===========================================================

    async def tick(self) -> None:
        """Advance the turn counter and close pages idle for >= 2 turns.

        Called by the lifecycle capability before each model request. A page
        opened in turn N has ``last_touched_turn = N``. If the agent does
        not touch it in turn N+1, ``last_touched_turn`` stays at N. By the
        start of turn N+2, ``current_turn - last_touched_turn >= 2`` → close.
        """
        self._turn_counter += 1
        threshold = self._turn_counter - 2
        to_close: list[_PageState] = []
        for pid in list(self._pages.keys()):
            state = self._pages.get(pid)
            if state is not None and state.last_touched_turn <= threshold:
                to_close.append(state)
                del self._pages[pid]
        for state in to_close:
            try:
                await state.page.close()
            except Exception:
                pass
            self._metrics.num_pages_auto_closed += 1

    async def close(self) -> None:
        """Close all pages and (if isolated) the private context."""
        states = list(self._pages.values())
        self._pages.clear()
        for state in states:
            try:
                await state.page.close()
            except Exception:
                pass
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
            Tool(self.browser_list_pages, name="browser_list_pages"),
        ]

    def lifecycle_capability(self) -> object:
        """Return a pydantic-ai ``Hooks`` capability that ticks this tool.

        The returned capability subscribes to ``before_model_request`` and
        invokes ``tick()`` on each model turn boundary. Pass it to
        ``Agent(capabilities=[...])``.
        """
        try:
            from pydantic_ai.capabilities import Hooks
        except ImportError as e:
            raise RuntimeError(
                "lifecycle_capability requires pydantic-ai with Hooks support. "
                "Upgrade pydantic-ai or call tool.tick() manually between turns."
            ) from e
        hooks = Hooks()

        @hooks.on.before_model_request
        async def _tick(ctx, request_context):  # type: ignore[no-untyped-def]
            await self.tick()
            return request_context

        return hooks

    def metrics(self) -> WebBrowserToolMetrics:
        return self._metrics

    # === Internals ===========================================================

    async def _ensure_manager(self) -> WebBrowserManager:
        if self._manager is None:
            self._manager = await WebBrowserManager.get(headless=self._headless)
        return self._manager

    async def _ensure_context(self) -> "BrowserContext":
        if self._isolated:
            if self._owned_context is None:
                manager = await self._ensure_manager()
                self._owned_context = await manager.new_isolated_context()
            return self._owned_context
        manager = await self._ensure_manager()
        return await manager.shared_context()

    def _unknown_page(self, page_id: int) -> str:
        open_ids = sorted(self._pages.keys())
        return f"no page with id {page_id}; open pages: {open_ids or 'none'}"

    def _on_popup_sync(self, page_id: int, popup: "Page") -> None:
        """Sync wrapper that schedules the async popup adoption."""
        asyncio.create_task(self._on_popup(page_id, popup))

    async def _on_popup(self, page_id: int, popup: "Page") -> None:
        """Adopt a site-popped tab as the active page for ``page_id``."""
        state = self._pages.get(page_id)
        if state is None:
            return  # original page was closed
        try:
            await popup.wait_for_load_state("domcontentloaded", timeout=_SETTLE_TIMEOUT_MS)
        except Exception:
            pass
        old_page = state.page
        state.page = popup
        try:
            popup_url = popup.url
        except Exception:
            popup_url = "(unknown)"
        state.popup_notice = (
            f"[note: previous action on page {page_id} opened a popup; "
            f"this tab is now {popup_url}]"
        )
        self._metrics.num_popups_adopted += 1
        if old_page is not None and old_page is not popup:
            try:
                await old_page.close()
            except Exception:
                pass
        popup.on("popup", lambda p, pid=page_id: self._on_popup_sync(pid, p))

    async def _settle(self, state: _PageState) -> None:
        try:
            await state.page.wait_for_load_state("networkidle", timeout=_SETTLE_TIMEOUT_MS)
        except Exception:
            pass

    def _resolve_ref(self, state: _PageState, ref: str) -> "Locator":
        if state.last_snapshot is None:
            raise _RefError(
                f"page {state.page_id}: no snapshot available; call any action first"
            )
        if ref not in state.last_snapshot.refs:
            available = sorted(state.last_snapshot.refs)
            raise _RefError(
                f"page {state.page_id}: unknown ref {ref!r}. "
                f"Available refs: {available[:30]}"
            )
        return state.page.locator(f"aria-ref={ref}")

    async def _format_response_for(self, state: _PageState) -> str:
        snapshot = await take_snapshot(state.page)
        state.last_snapshot = snapshot

        inlined = set(_REF_PATTERN.findall(snapshot.markdown_content))
        remaining = [
            e for e in snapshot.interactive_elements if e.ref not in inlined
        ]

        parts: list[str] = []
        if state.popup_notice is not None:
            parts.append(state.popup_notice)
            parts.append("")
            state.popup_notice = None
        parts.append(f"[page={state.page_id}]")
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
