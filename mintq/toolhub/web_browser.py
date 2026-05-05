"""Concurrent multi-agent, multi-tab browser tool built on Playwright.

Designed for fleets of agents browsing in parallel within one Python
process: many agents share one Chromium (not one each), each can open
many tabs simultaneously (not one foreground at a time), and idle
tabs auto-close between turns (no manual cleanup).  The browser-use
alternative — Chromium-per-session, single foreground tab — costs
~15 GB at 50 agents and forces every multi-source workflow through
subagent fan-out.

What this module adds on top of Playwright (and differs from browser-use)
=========================================================================

**One Chromium, many isolated agents.**  Singleton ``WebBrowserManager``
owns one Chromium + a shared ``BrowserContext``; many ``WebBrowserTool``
instances coexist in-process.  ``isolated=True`` opts into a private
context when cookie/storage isolation matters.  Browser-use launches one
Chromium per session — at 50 agents that's 50 browsers vs one here.

**Multi-tab state per tool.**  Each tool tracks ``dict[str, _TabState]``
keyed by short ``"t1"``/``"t2"``-style ids; ``browser_navigate`` opens
a *new* tab each call, addressed by ``tab="t3"`` in subsequent actions.
Lets the LLM fan out several parallel ``browser_navigate`` calls in one
turn (search-and-explore), then drill in next turn.  Browser-use's
session is single-tab; multi-tab there means subagent fan-out (N LLM
loops).

**Turn-based auto-cleanup.**  Tabs auto-close at the next turn if not
interacted with.  ``lifecycle_capability()`` returns a pydantic-ai
``Hooks`` capability that fires ``tick()`` on ``before_model_request``;
``tick()`` increments the turn counter and closes idle tabs.  No
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

# After ``load`` fires we wait for ``networkidle`` to give SPAs time to
# render their JS-injected content. Capped because some sites (Google Flights,
# dashboards with continuous polling) never reach networkidle within reason.
# 10s comfortably covers most modern SPAs (React apps with API calls, news
# sites, social feeds) while bounding worst-case latency on streaming pages.
_NETWORKIDLE_WAIT_MS = 10_000

# Tighter budget for in-site navigations (click/type that stays on same host).
# Same-domain navs typically reuse cached CSS/JS and settle faster — we don't
# need the full SPA-rendering budget. Borrowed from browser-use's heuristic.
_NETWORKIDLE_WAIT_MS_SAME_DOMAIN = 3_000

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

# Roles considered "context-bearing" — used to disambiguate identical-looking
# interactive elements in the "Other interactive elements" listing (e.g.,
# multiple "View more" buttons distinguished by their nearest heading).
_CONTEXT_ROLES: frozenset[str] = frozenset(
    {
        "heading",
        "region",
        "main",
        "article",
        "form",
        "search",
        "dialog",
        "listitem",
        "row",
        "rowgroup",
        "tab",
        "tabpanel",
        "figure",
        "group",
        "navigation",
        "complementary",
        "contentinfo",
        "banner",
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
    num_presses: int = 0
    num_selects: int = 0
    num_waits: int = 0
    num_errors: int = 0
    num_popups_adopted: int = 0
    num_tabs_auto_closed: int = 0


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
    parent_context: tuple[str, str] | None = None  # (role, name) of nearest named ancestor


@dataclass
class PageSnapshot:
    url: str
    title: str
    interactive_elements: list[InteractiveElement] = field(default_factory=list)
    markdown_content: str = ""
    refs: set[str] = field(default_factory=set)


def parse_interactive_elements(aria_yaml: str) -> list[InteractiveElement]:
    """Extract interactive elements from an aria-snapshot YAML string.

    For each interactive element, also captures the nearest preceding
    context-bearing element (heading, region, listitem, etc.) at less-or-
    equal indentation — used to disambiguate identical-looking buttons
    (e.g., multiple "View more" buttons in different cards) when listed
    in the "Other interactive elements" section.
    """
    lines = aria_yaml.split("\n")
    elements: list[InteractiveElement] = []
    # Stack of (indent, role, name) — context-bearing elements still in scope.
    context_stack: list[tuple[int, str, str]] = []

    for i, line in enumerate(lines):
        m = _ARIA_LINE_PATTERN.match(line)
        if m is None:
            continue
        indent = len(m.group("indent"))
        role = m.group("role")
        name = m.group("name") or ""
        ref = m.group("ref")

        # Pop ancestors at strictly greater indent (siblings stay).
        while context_stack and context_stack[-1][0] > indent:
            context_stack.pop()

        # Push this element if it can serve as context for later siblings/children.
        if role in _CONTEXT_ROLES and name:
            context_stack.append((indent, role, name))

        if role not in _INTERACTIVE_ROLES:
            continue

        href: str | None = None
        if role == "link":
            # Look ahead within the link's indented block for `- /url:`
            for next_line in lines[i + 1 : i + 6]:
                if not next_line.strip():
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent:
                    break
                um = _ARIA_URL_PATTERN.match(next_line)
                if um is not None:
                    href = um.group("url")
                    break

        ctx: tuple[str, str] | None = None
        if context_stack:
            _, c_role, c_name = context_stack[-1]
            ctx = (c_role, c_name)

        elements.append(
            InteractiveElement(ref=ref, role=role, name=name, href=href, parent_context=ctx)
        )
    return elements


def render_interactive_elements(elements: list[InteractiveElement]) -> str:
    """Render a flat list of interactive elements for the LLM.

    Each line: ``- [ref=eN] role "name" → href (under: heading "X")``.
    Parent-context suffix lets the agent disambiguate same-named buttons.
    """
    if not elements:
        return "(no interactive elements)"
    out: list[str] = []
    for e in elements:
        line = f"- [ref={e.ref}] {e.role}"
        if e.name:
            line += f' "{e.name}"'
        if e.href:
            line += f" → {e.href}"
        if e.parent_context:
            ctx_role, ctx_name = e.parent_context
            line += f' (under: {ctx_role} "{ctx_name}")'
        out.append(line)
    return "\n".join(out)


def inline_link_refs(
    markdown: str, elements: list[InteractiveElement]
) -> tuple[str, list[InteractiveElement]]:
    """Inject ``[ref=eN]`` after matching ``[name](href)`` links in markdown.

    Returns ``(modified_markdown, elements_not_inlined)``. Non-link elements,
    links without href or name, and links whose markdown form doesn't match
    all fall through to the remaining list.
    """
    out = markdown
    consumed: set[str] = set()
    for e in elements:
        if e.role != "link" or not e.href or not e.name:
            continue
        pattern = re.compile(
            r"(\[" + re.escape(e.name) + r"\]\("
            + re.escape(e.href) + r'(?:\s+"[^"]*")?\))(?!\s*\[ref=)'
        )
        new_out, n = pattern.subn(r"\1 [ref=" + e.ref + r"]", out, count=1)
        if n > 0:
            out = new_out
            consumed.add(e.ref)
    remaining = [e for e in elements if e.ref not in consumed]
    return out, remaining


# JS-side visibility filter. Returns the page's HTML with hidden subtrees
# removed (display:none, visibility:hidden, aria-hidden=true, opacity:0,
# zero-size, closed <dialog>/<details>, <template>, <noscript>).
# Catches duplicate content rendered for tab toggles, mobile/desktop
# variants, SEO duplicates that aren't visible to a sighted user.
_VISIBLE_HTML_JS = """
() => {
    const isVisible = (el) => {
        if (!el || el.hidden) return false;
        if (el.matches && el.matches('[aria-hidden="true"]')) return false;
        const tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (tag === 'template' || tag === 'noscript') return false;
        if (tag === 'dialog' && !el.open) return false;
        if (tag === 'details' && !el.open) {
            // keep <summary> children only — handled below by walk skipping siblings
        }
        const style = window.getComputedStyle(el);
        if (style.display === 'none') return false;
        if (style.visibility === 'hidden') return false;
        if (style.opacity === '0') return false;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return false;
        return true;
    };
    const walk = (el) => {
        if (!isVisible(el)) return null;
        const clone = el.cloneNode(false);
        for (const child of el.childNodes) {
            if (child.nodeType === Node.ELEMENT_NODE) {
                const c = walk(child);
                if (c) clone.appendChild(c);
            } else {
                clone.appendChild(child.cloneNode(true));
            }
        }
        return clone;
    };
    const root = walk(document.documentElement);
    return root ? root.outerHTML : document.documentElement.outerHTML;
}
"""


async def extract_markdown(page: "Page") -> str:
    """Extract clean markdown from the live rendered page.

    Pipeline: JS-side visibility filter (drops hidden duplicates) →
    lxml.Cleaner (strips scripts/styles/nav/footer/etc.) → markdownify.
    """
    try:
        html = await page.evaluate(_VISIBLE_HTML_JS)
    except Exception:
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
        from markdownify import markdownify
    except ImportError:
        return "(error: markdownify is not installed)"

    md = markdownify(
        cleaned_html,
        heading_style="ATX",
        strip=["script", "style", "img"],
        bullets="-",
        escape_asterisks=False,
        escape_underscores=False,
        escape_misc=False,
        autolinks=False,
        default_title=False,
    )
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
    markdown = await extract_markdown(page)
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
# Browser process manager
# ---------------------------------------------------------------------------


class WebBrowserManager:
    """Owns a Chromium browser process and a shared ``BrowserContext``.

    Mental model — same as Chrome on your laptop:

    - ``Chromium browser`` ≈ one running Chrome.app
    - ``BrowserContext`` ≈ one Chrome profile (or incognito window):
      own cookies, own storage, fully isolated from siblings
    - ``Page`` ≈ one tab inside a context

    Get the process-wide default via the module-level ``default_manager()``
    accessor; construct directly only for tests or non-default lifecycle
    needs.
    """

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._shared_context: BrowserContext | None = None
        self._lock = asyncio.Lock()

    async def shared_context(self) -> "BrowserContext":
        """Return the shared BrowserContext, launching the browser if needed."""
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

    async def new_isolated_context(self) -> "BrowserContext":
        """Create a fresh private BrowserContext for tools that need isolation."""
        async with self._lock:
            browser = await self._ensure_browser_locked()
        return await browser.new_context(
            user_agent=_USER_AGENT,
            accept_downloads=False,
        )

    async def close(self) -> None:
        """Tear down the shared context, browser, and Playwright runtime."""
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

    # internals ---------------------------------------------------------------

    async def _ensure_browser_locked(self) -> "Browser":
        """Launch Chromium if not already running. Caller must hold ``self._lock``."""
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
# Default manager (process-wide singleton accessor)
# ---------------------------------------------------------------------------

_default_manager: WebBrowserManager | None = None
_default_manager_lock = asyncio.Lock()


async def default_manager(headless: bool = True) -> WebBrowserManager:
    """Return the process-wide default manager, lazily creating it.

    ``headless`` is honored only on the first call; subsequent calls
    return the existing manager regardless of the value passed.
    """
    global _default_manager
    if _default_manager is not None:
        return _default_manager
    async with _default_manager_lock:
        if _default_manager is None:
            _default_manager = WebBrowserManager(headless=headless)
        return _default_manager


async def reset_default_manager() -> None:
    """Close and discard the process-wide default manager.

    Mainly useful for tests that need a fresh browser between runs.
    """
    global _default_manager
    async with _default_manager_lock:
        if _default_manager is not None:
            await _default_manager.close()
            _default_manager = None


# ---------------------------------------------------------------------------
# Internal exceptions
# ---------------------------------------------------------------------------


class _RefError(Exception):
    """Raised when a snapshot ref cannot be resolved."""


# ---------------------------------------------------------------------------
# Per-tab state
# ---------------------------------------------------------------------------


@dataclass
class _TabState:
    """Per-tab state held by a multi-tab WebBrowserTool.

    The internal ``page`` field holds Playwright's ``Page`` object — that's
    Playwright's name for what users call a tab. We expose ``tab_id`` (a
    ``"t1"``-style string) to the LLM rather than the Playwright object.
    """

    tab_id: str
    page: "Page"
    last_touched_turn: int
    last_snapshot: PageSnapshot | None = None
    popup_notice: str | None = None
    op_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


async def format_tab_response(state: _TabState) -> str:
    """Build the LLM-facing response for a tab state.

    Takes a fresh snapshot, inlines refs into body markdown, and renders the
    page + other-elements view. Mutates ``state.last_snapshot`` (sets the new
    snapshot) and ``state.popup_notice`` (consumes any pending popup notice).
    """
    snapshot = await take_snapshot(state.page)
    state.last_snapshot = snapshot

    annotated_md, remaining = inline_link_refs(
        snapshot.markdown_content, snapshot.interactive_elements
    )

    parts: list[str] = []
    if state.popup_notice is not None:
        parts.append(state.popup_notice)
        parts.append("")
        state.popup_notice = None
    parts.append(f"[tab={state.tab_id}]")
    parts.append(f"URL: {snapshot.url}")
    if snapshot.title:
        parts.append(f"Title: {snapshot.title}")
    parts.append("")
    parts.append("# Page")
    parts.append(annotated_md or "(no content extracted)")
    if remaining:
        parts.append("")
        parts.append("# Other interactive elements")
        parts.append(render_interactive_elements(remaining))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Per-agent tool
# ---------------------------------------------------------------------------


class WebBrowserTool:
    """Per-agent stateful browser tool with multi-tab support.

    One instance can manage many tabs within a shared (or private)
    BrowserContext. Each ``browser_navigate`` call opens a NEW tab; the
    LLM addresses subsequent actions via ``tab="t1"`` to refer back. Tabs
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
        max_tabs: int = 10,
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
            max_tabs: Cap on simultaneously-open tabs for this tool.
                Returns an error if exceeded; idle tabs auto-close at
                the next turn boundary.
            headless: Run Chromium headless. Set False for visible-window
                debugging. Honored only on first manager construction;
                subsequent tools share the existing browser regardless.
        """
        self._manager = manager
        self._isolated = isolated
        self._max_tabs = max_tabs
        self._headless = headless
        self._owned_context: BrowserContext | None = None
        self._tabs: dict[str, _TabState] = {}
        self._next_tab_seq = 1
        self._turn_counter = 0
        self._metrics = WebBrowserToolMetrics()

    # === LLM-facing tool methods ============================================

    async def browser_navigate(self, url: str) -> str:
        """Open a NEW tab at ``url`` and return its post-load snapshot.

        Each call opens a fresh tab — previously-opened tabs remain open.
        Use the ``tab`` id from the response (e.g., ``"t3"``) in subsequent
        action calls (``browser_click``, etc.) to interact with this tab.
        Tabs auto-close if not interacted with on the next agent turn.

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
        if len(self._tabs) >= self._max_tabs:
            return self._format_error(
                f"max_tabs ({self._max_tabs}) reached. "
                f"Open tabs: {sorted(self._tabs.keys())}. "
                f"Idle tabs auto-close at the next turn boundary."
            )

        tab_id = f"t{self._next_tab_seq}"
        self._next_tab_seq += 1

        try:
            ctx = await self._ensure_context()
            page = await ctx.new_page()
        except Exception as e:
            return self._format_error(f"failed to open tab: {self._error_message(e)}")

        page.on("popup", lambda p, tid=tab_id: self._on_popup_sync(tid, p))

        try:
            # Two-phase wait: ``load`` for the navigation guarantee, then a
            # bounded ``networkidle`` to give SPAs time to render their JS
            # content. Pure ``networkidle`` goto can hang for 30s+ on
            # streaming sites (Google Flights); pure ``load`` returns before
            # SPA content appears. The bounded follow-up balances both.
            await page.goto(url, wait_until="load", timeout=_NAV_TIMEOUT_MS)
            try:
                await page.wait_for_load_state("networkidle", timeout=_NETWORKIDLE_WAIT_MS)
            except Exception:
                pass  # SPA never settled; proceed with current state
        except Exception as e:
            try:
                await page.close()
            except Exception:
                pass
            return self._format_error(f"navigation failed: {self._error_message(e)}")

        state = _TabState(tab_id=tab_id, page=page, last_touched_turn=self._turn_counter)
        self._tabs[tab_id] = state
        return await format_tab_response(state)

    async def browser_click(self, tab: str, ref: str) -> str:
        """Click an interactive element on a specific tab.

        Args:
            tab: The id of the tab to act on, e.g. ``"t1"`` (from a previous response).
            ref: The ref string from that tab's latest snapshot, e.g. ``"e15"``.
        """
        self._metrics.num_clicks += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
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
            return await format_tab_response(state)

    async def browser_type(self, tab: str, ref: str, text: str, submit: bool = False) -> str:
        """Type text into an editable element on a specific tab.

        Args:
            tab: The id of the tab to act on, e.g. ``"t1"``.
            ref: The ref string of the input element, e.g. ``"e15"``.
            text: The text to type. Replaces existing content.
            submit: If True, press Enter after typing. Without submit the
                response is a short ack since the page state hasn't changed
                beyond the input field's value (which the agent already knows).
        """
        self._metrics.num_types += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
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
            if not submit:
                # No submit → page state didn't change in any way the agent
                # doesn't already know. Skip the full re-snapshot to save tokens.
                return f"[tab={tab}] typed into ref={ref}"
            return await format_tab_response(state)

    async def browser_scroll(
        self, tab: str, direction: Literal["up", "down", "top", "bottom"]
    ) -> str:
        """Scroll a specific tab.

        Args:
            tab: The id of the tab to scroll, e.g. ``"t1"``.
            direction: One of ``"up"``, ``"down"``, ``"top"``, ``"bottom"``.
        """
        self._metrics.num_scrolls += 1
        if direction not in ("up", "down", "top", "bottom"):
            return self._format_error(
                f"invalid direction {direction!r}; expected up/down/top/bottom"
            )
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
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
            return await format_tab_response(state)

    async def browser_back(self, tab: str) -> str:
        """Navigate back in a specific tab's history.

        Args:
            tab: The id of the tab to navigate back on, e.g. ``"t1"``.
        """
        self._metrics.num_backs += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        async with state.op_lock:
            try:
                await state.page.go_back(wait_until="load", timeout=_NAV_TIMEOUT_MS)
                try:
                    await state.page.wait_for_load_state("networkidle", timeout=_NETWORKIDLE_WAIT_MS)
                except Exception:
                    pass
            except Exception as e:
                return self._format_error(f"back failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await format_tab_response(state)

    async def browser_press(self, tab: str, key: str) -> str:
        """Press a keyboard key on a tab (no specific element required).

        Most useful for dismissing modals (``"Escape"``), submitting forms
        (``"Enter"``), and tab navigation (``"Tab"``). Operates on whichever
        element currently has focus, or at page level for keys like Escape.

        Args:
            tab: The id of the tab to act on, e.g. ``"t1"``.
            key: A Playwright key name — e.g. ``"Escape"``, ``"Enter"``,
                ``"Tab"``, ``"ArrowDown"``, ``"PageDown"``, ``"Backspace"``,
                or a chord like ``"Control+a"`` / ``"Meta+v"``.
        """
        self._metrics.num_presses += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        async with state.op_lock:
            try:
                await state.page.keyboard.press(key)
                await self._settle(state)
            except Exception as e:
                return self._format_error(f"press failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await format_tab_response(state)

    async def browser_select(self, tab: str, ref: str, option: str) -> str:
        """Select an option from a native ``<select>`` dropdown.

        For native HTML ``<select>`` elements (combobox role). Use this
        instead of click+click — Playwright's ``select_option`` handles
        native dropdowns reliably across browsers.

        Args:
            tab: The id of the tab to act on, e.g. ``"t1"``.
            ref: The ref of the ``<select>`` element, e.g. ``"e15"``.
            option: The option to choose, matched by visible label or by
                value attribute (Playwright tries both).
        """
        self._metrics.num_selects += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        async with state.op_lock:
            try:
                locator = self._resolve_ref(state, ref)
                await locator.select_option(option, timeout=_SETTLE_TIMEOUT_MS)
                await self._settle(state)
            except _RefError as e:
                return self._format_error(str(e))
            except Exception as e:
                return self._format_error(f"select failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await format_tab_response(state)

    async def browser_wait(self, tab: str, seconds: float = 3.0) -> str:
        """Sleep for ``seconds`` seconds, then re-snapshot the tab.

        Useful when a previous action triggered slow content loading and
        the auto-settle wait wasn't long enough (e.g., heavy dashboards
        that render a few seconds after the network goes idle).

        Args:
            tab: The id of the tab to re-snapshot afterward, e.g. ``"t1"``.
            seconds: How long to wait, capped at 30s.
        """
        self._metrics.num_waits += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        seconds = max(0.0, min(seconds, 30.0))
        async with state.op_lock:
            await asyncio.sleep(seconds)
            state.last_touched_turn = self._turn_counter
            return await format_tab_response(state)

    # === Lifecycle ===========================================================

    async def tick(self) -> None:
        """Advance the turn counter and close idle tabs.

        Called by the lifecycle capability before each model request.

        Cleanup only runs on turns that follow browser activity. If the
        previous turn had no browser actions (agent was doing SQL, planning,
        etc.), all tabs are preserved — the agent can return to its browser
        context later. When the agent does interact with the browser again,
        the normal "tabs untouched in the past 2 turns get closed" rule
        kicks back in.
        """
        self._turn_counter += 1
        prev_turn = self._turn_counter - 1
        # Skip cleanup if no browser activity in the previous turn.
        if not any(s.last_touched_turn == prev_turn for s in self._tabs.values()):
            return
        threshold = self._turn_counter - 2
        to_close: list[_TabState] = []
        for tid in list(self._tabs.keys()):
            state = self._tabs.get(tid)
            if state is not None and state.last_touched_turn <= threshold:
                to_close.append(state)
                del self._tabs[tid]
        for state in to_close:
            try:
                await state.page.close()
            except Exception:
                pass
            self._metrics.num_tabs_auto_closed += 1

    async def close(self) -> None:
        """Close all tabs and (if isolated) the private context."""
        states = list(self._tabs.values())
        self._tabs.clear()
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
            Tool(self.browser_press, name="browser_press"),
            Tool(self.browser_select, name="browser_select"),
            Tool(self.browser_wait, name="browser_wait"),
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
            self._manager = await default_manager(headless=self._headless)
        return self._manager

    async def _ensure_context(self) -> "BrowserContext":
        if self._isolated:
            if self._owned_context is None:
                manager = await self._ensure_manager()
                self._owned_context = await manager.new_isolated_context()
            return self._owned_context
        manager = await self._ensure_manager()
        return await manager.shared_context()

    def _unknown_tab(self, tab_id: str) -> str:
        open_ids = sorted(self._tabs.keys())
        return f"no tab {tab_id!r}; open tabs: {open_ids or 'none'}"

    def _on_popup_sync(self, tab_id: str, popup: "Page") -> None:
        """Sync wrapper that schedules the async popup adoption."""
        asyncio.create_task(self._on_popup(tab_id, popup))

    async def _on_popup(self, tab_id: str, popup: "Page") -> None:
        """Adopt a site-popped tab as the active page for ``tab_id``."""
        state = self._tabs.get(tab_id)
        if state is None:
            return  # original tab was closed
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
            f"[note: previous action on tab {tab_id} opened a popup; "
            f"this tab is now {popup_url}]"
        )
        self._metrics.num_popups_adopted += 1
        if old_page is not None and old_page is not popup:
            try:
                await old_page.close()
            except Exception:
                pass
        popup.on("popup", lambda p, tid=tab_id: self._on_popup_sync(tid, p))

    async def _settle(self, state: _TabState) -> None:
        timeout = _NETWORKIDLE_WAIT_MS
        if state.last_snapshot is not None:
            try:
                prev_host = urlparse(state.last_snapshot.url).netloc
                cur_host = urlparse(state.page.url).netloc
                if prev_host and prev_host == cur_host:
                    timeout = _NETWORKIDLE_WAIT_MS_SAME_DOMAIN
            except Exception:
                pass
        try:
            await state.page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass

    def _resolve_ref(self, state: _TabState, ref: str) -> "Locator":
        if state.last_snapshot is None:
            raise _RefError(
                f"page {state.tab_id}: no snapshot available; call any action first"
            )
        if ref not in state.last_snapshot.refs:
            available = sorted(state.last_snapshot.refs)
            raise _RefError(
                f"page {state.tab_id}: unknown ref {ref!r}. "
                f"Available refs: {available[:30]}"
            )
        return state.page.locator(f"aria-ref={ref}")

    def _format_error(self, msg: str) -> str:
        self._metrics.num_errors += 1
        return f"(error: {msg})"

    @staticmethod
    def _error_message(e: Exception) -> str:
        msg = str(e).strip()
        return msg or e.__class__.__name__
