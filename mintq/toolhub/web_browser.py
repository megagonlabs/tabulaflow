"""Multi-agent, multi-tab browser tool built on Playwright designed
for massive parallelization.

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
session is single-tab.

**Turn-based auto-cleanup.**  Tabs auto-close at the next turn if not
interacted with.  No ``browser_close`` exposed — the agent declares
interest by interaction.

**Markdown with click affordances inline.**  Each tool response is one
document: page text rendered as markdown with ``[ref=eN]`` markers
placed right after each link, button, or input.  Every interactive
element is a self-contained single-line atom (``[text](url) [ref=eN]``
for links; ``role "name" [ref=eN]`` for buttons / form controls / etc.)
so the agent can locate one with a single grep / SQL regex.  See
:mod:`mintq.toolhub.aria_to_markdown` for the full atom-shape reference.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal
from urllib.parse import urlparse

from pydantic import BaseModel
from pydantic_ai import Tool

from .aria_to_markdown import (
    extract_refs,
    render_aria_markdown,
)

if TYPE_CHECKING:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Locator,
        Page,
        Playwright,
    )
    from pydantic_ai.capabilities import Hooks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NAV_TIMEOUT_MS = 30_000
_SETTLE_TIMEOUT_MS = 10_000

# After ``load`` fires we wait for ``networkidle`` to give SPAs time to
# render their JS-injected content. Capped because chatty SPAs (Google Flights,
# dashboards, anything with continuous polling/analytics) never reach
# networkidle. 5s catches the median cross-domain initial render while
# bounding the wasted budget on never-settling pages. Lower would be
# tempting but starts to clip legitimate first-load fetches; the agent has
# ``browser_wait`` for the rare slower case.
_NETWORKIDLE_WAIT_MS = 5_000

# Tighter budget for in-site navigations (click/type that stays on same host).
# Same-domain navs typically reuse cached CSS/JS and settle faster — we don't
# need the full SPA-rendering budget. Borrowed from browser-use's heuristic.
_NETWORKIDLE_WAIT_MS_SAME_DOMAIN = 3_000

# How long a no-submit ``browser_type`` waits for an autocomplete dropdown to
# appear before snapshotting. Short on purpose: when typing surfaces options we
# return quickly; when it doesn't (a plain text field) we only pay this once.
_AUTOCOMPLETE_WAIT_MS = 1_500

# Fixed sleep after the networkidle attempt and before snapshotting, to give
# Chromium time to finish computing accessible names for lazily-hydrated nodes.
# Without it, sites that never reach networkidle (Google Flights, dashboards
# with continuous polling) snapshot mid-hydration: buttons appear with no
# names, form controls show as bare ``textbox [ref=eN]``, icons render as
# bare ``[]``. 300ms (browser-use's default) wasn't enough for Google Flights
# in practice — accessible names on the date/origin/destination fields lagged
# past that window after combobox expansion. 1s is a heavier baseline tax but
# eliminates the partial-hydration class of bug for the chatty SPAs that
# motivated this. If/when it shows up as a latency complaint, switch to an
# active stability check (sample-sleep-sample on the aria YAML) instead.
_POST_LOAD_SETTLE_MS = 1_000


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# Names of the LLM-facing browser action tools (see ``as_pydantic_ai_tools``).
# Single source of truth for message-store allowlists that need to know which
# tool returns are browser snapshots (and thus truncation candidates).
BROWSER_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "browser_navigate",
        "browser_click",
        "browser_type",
        "browser_scroll",
        "browser_back",
        "browser_press",
        "browser_select",
        "browser_wait",
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
    num_clicks_dispatched_through_overlay: int = 0


# ---------------------------------------------------------------------------
# Snapshot: clean markdown derived from a single aria-tree walk.
#
# Refs resolve via Playwright's ``aria-ref=eN`` locator. The markdown is
# rendered from the same YAML tree so refs land inline by construction —
# no second-pass interactive-elements list, no "Other" cross-check, no HTML.
# ---------------------------------------------------------------------------


@dataclass
class PageSnapshot:
    url: str
    title: str
    markdown_content: str = ""
    refs: list[str] = field(default_factory=list)  # in document order
    aria_yaml: str = ""  # raw aria YAML, kept for targeted scans (e.g. options)


async def take_snapshot(page: "Page") -> PageSnapshot:
    """Capture the current page as markdown rendered from a single aria walk.

    Refs are inline in the markdown by construction. ``refs`` powers ref
    validation in ``_resolve_ref``; ``aria_yaml`` is kept for targeted scans
    (e.g., extracting autocomplete options on ``browser_type``).
    """
    try:
        aria_yaml = await page.aria_snapshot(mode="ai", timeout=_SETTLE_TIMEOUT_MS)
    except Exception as e:
        aria_yaml = ""
        logger.debug("aria_snapshot failed: %s", e)
    title = ""
    try:
        title = await page.title()
    except Exception:
        pass
    return PageSnapshot(
        url=page.url,
        title=title,
        markdown_content=render_aria_markdown(aria_yaml),
        refs=extract_refs(aria_yaml),
        aria_yaml=aria_yaml,
    )


# ---------------------------------------------------------------------------
# Browser process manager
# ---------------------------------------------------------------------------


class _PageBudget:
    """Process-wide cap on simultaneously-open browser pages.

    A permit is taken before a tab opens and returned when it closes, bounding
    total live Chromium pages across every ``WebBrowserTool`` — the dominant
    memory cost under wide/deep subagent fan-out.

    Acquire policy (chosen by the caller):
    - ``block=True`` waits (indefinitely, event-driven) for a free slot. Use it
      only when the caller holds no permit yet (a tool's first tab): waiting
      while holding nothing is deadlock-safe (the waiter is in no cycle) and
      never fails a one-tab task.
    - ``block=False`` returns immediately. Use it once the caller already holds
      a permit (a tool's 2nd+ tab) so a holder never blocks-while-holding, which
      would risk deadlock when permit-holders await permit-seekers.
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
    """Owns a Chromium browser process and a shared ``BrowserContext``.

    Mental model — same as Chrome on your laptop:

    - ``Chromium browser`` ≈ one running Chrome.app
    - ``BrowserContext`` ≈ one Chrome profile (or incognito window):
      own cookies, own storage, fully isolated from siblings
    - ``Page`` ≈ one tab inside a context

    Also owns a process-wide :class:`_PageBudget` capping simultaneously-open
    pages across all tools that share this manager.

    Get the process-wide default via the module-level ``default_manager()``
    accessor; construct directly only for tests or non-default lifecycle
    needs.
    """

    def __init__(self, headless: bool = True, max_pages: int | None = None) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._shared_context: BrowserContext | None = None
        self._lock = asyncio.Lock()
        self._page_budget = _PageBudget(max_pages)

    async def acquire_page(self, *, block: bool) -> bool:
        """Take a page permit. See :class:`_PageBudget` for the ``block`` policy."""
        return await self._page_budget.acquire(block=block)

    async def release_page(self) -> None:
        """Return a page permit taken by :meth:`acquire_page`."""
        await self._page_budget.release()

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
                "playwright is not installed. Install with: uv add playwright && uv run playwright install chromium"
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
            from mintq.config import mintq_config

            _default_manager = WebBrowserManager(headless=headless, max_pages=mintq_config.max_browser_tabs)
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


_REF_PATTERN = re.compile(r"^e\d+$")


# Common natural-language aliases for keys, mapped to canonical Playwright names.
# LLMs frequently use these spellings ("ctrl+a", "esc", "cmd+v"); without
# normalization the press silently fails.
_KEY_ALIASES: dict[str, str] = {
    "ctrl": "Control",
    "control": "Control",
    "alt": "Alt",
    "option": "Alt",
    "meta": "Meta",
    "cmd": "Meta",
    "command": "Meta",
    "shift": "Shift",
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "delete": "Delete",
    "del": "Delete",
    "backspace": "Backspace",
    "escape": "Escape",
    "esc": "Escape",
    "space": " ",
    "spacebar": " ",
    "up": "ArrowUp",
    "down": "ArrowDown",
    "left": "ArrowLeft",
    "right": "ArrowRight",
    "pageup": "PageUp",
    "pagedown": "PageDown",
    "home": "Home",
    "end": "End",
}


def _normalize_key(key: str) -> str:
    """Map natural aliases (``ctrl``, ``cmd``, ``esc``, ``space``, ``up`` …) to
    canonical Playwright names. Preserves chords (``"ctrl+a"`` → ``"Control+a"``)
    and leaves unrecognized parts unchanged.
    """
    if "+" in key:
        return "+".join(_KEY_ALIASES.get(p.strip().lower(), p) for p in key.split("+"))
    return _KEY_ALIASES.get(key.strip().lower(), key)


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

    Takes a fresh snapshot and emits the markdown. Refs land inline by
    construction via the aria-driven renderer — orphans get anchored to their
    parent automatically — so no cross-check or auxiliary list is needed.
    Mutates ``state.last_snapshot`` and consumes any pending popup notice.
    """
    snapshot = await take_snapshot(state.page)
    state.last_snapshot = snapshot

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
    parts.append("---")
    parts.append(snapshot.markdown_content or "(no content extracted)")
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
        headless: bool | None = None,
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
            headless: Run Chromium headless. None (default) reads from
                ``mintq_config.browser_headless`` so every tool in the
                process — including subagent-spawned ones — shares the
                same setting. Honored only on first manager construction;
                subsequent tools share the existing browser regardless.
        """
        if headless is None:
            from mintq.config import mintq_config
            headless = mintq_config.browser_headless
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

    async def browser_navigate(self, url: str, tab: str | None = None) -> str:
        """Navigate to ``url`` and return the post-load snapshot.

        By default (``tab=None``) opens a NEW tab. Pass an existing ``tab``
        id (e.g. ``"t3"``) to navigate that tab in place instead — useful
        when the tab cap is reached, or when you want the tab's id and
        back-history to stay stable across the URL change.

        The snapshot is markdown rendered from the page's accessibility
        tree.  Every interactive element appears as a self-contained
        single-line atom followed by ``[ref=eN]``::

            [text](url) [ref=eN]            link
            button "name" [ref=eN]          button (also: clickable "text" [ref=eN])
            role "name" = "value" [ref=eN]  form controls (textbox/combobox/...)
            ![alt]() [ref=eN]               img
            option "name" [ref=eN]          live listbox option

        Pass that ``ref`` id to ``browser_click`` / ``browser_type`` /
        ``browser_select`` to act on the element.  Atoms may appear
        mid-line.

        Refs are per-snapshot, NOT stable element ids. Every tool response
        for a tab renumbers them from scratch — even on a visually unchanged
        page, DOM mutations or AJAX can shift the assignment. Only refs from
        the tab's MOST RECENT response are valid; never reuse an earlier ref.

        Each new-tab call opens a fresh tab — previously-opened tabs remain
        open. Use the ``tab`` id from the response (e.g., ``"t3"``) in
        subsequent action calls (``browser_click``, etc.) to interact with
        this tab. Tabs auto-close if not interacted with on the next agent
        turn.

        Issue multiple navigates in parallel within one turn to scan
        several URLs concurrently.

        Args:
            url: An ``http://`` or ``https://`` URL.
            tab: If set, navigate this existing tab in place instead of
                opening a new one.
        """
        self._metrics.num_navigates += 1
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return self._format_error(f"unsupported URL scheme {parsed.scheme!r}; only http/https allowed")
        if not parsed.netloc:
            return self._format_error("invalid URL — missing host")

        if tab is not None:
            state = self._tabs.get(tab)
            if state is None:
                return self._format_error(self._unknown_tab(tab))
            is_new = False
        else:
            state, err = await self._open_new_tab()
            if state is None:
                return err or self._format_error("failed to open tab")
            is_new = True

        async with state.op_lock:
            try:
                await self._goto(state.page, url)
            except Exception as e:
                if is_new:
                    await self._discard_tab(state)
                return self._format_error(f"navigation failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await format_tab_response(state)

    async def _goto(self, page: "Page", url: str) -> None:
        """Two-phase wait: ``load`` for the navigation guarantee, then a bounded
        ``networkidle`` to give SPAs time to render their JS content. Pure
        ``networkidle`` goto can hang for 30s+ on streaming sites (Google
        Flights); pure ``load`` returns before SPA content appears. The bounded
        follow-up balances both. A short fixed sleep afterward lets Chromium
        finish computing accessible names on sites that never reach networkidle.
        """
        await page.goto(url, wait_until="load", timeout=_NAV_TIMEOUT_MS)
        try:
            await page.wait_for_load_state("networkidle", timeout=_NETWORKIDLE_WAIT_MS)
        except Exception:
            pass  # SPA never settled; proceed with current state
        await asyncio.sleep(_POST_LOAD_SETTLE_MS / 1000)

    async def _open_new_tab(self) -> tuple["_TabState | None", str | None]:
        """Reserve a tab slot, take a permit, and open a fresh page.

        Returns ``(state, None)`` on success, or ``(None, error_response)`` if
        the tab cap is reached, the page budget is exhausted, or the underlying
        ``new_page`` call fails. On failure no state is registered and any
        permit taken has been released.
        """
        if len(self._tabs) >= self._max_tabs:
            return None, self._format_error(
                f"max_tabs ({self._max_tabs}) reached. "
                f"Open tabs: {sorted(self._tabs.keys())}. "
                f"Pass tab=<id> to reuse one, or idle them so they auto-close at the next turn boundary."
            )

        # Take a page permit from the process-wide budget before opening a tab.
        # First tab (we hold none) may block briefly for a slot; later tabs
        # fast-fail so a permit-holder never blocks while holding.
        manager = await self._ensure_manager()
        if not await manager.acquire_page(block=len(self._tabs) == 0):
            return None, self._format_error(
                "browser at capacity — pass tab=<id> to reuse an existing tab, "
                "or reduce parallelism and retry"
            )

        try:
            ctx = await self._ensure_context()
            page = await ctx.new_page()
        except Exception as e:
            await manager.release_page()
            return None, self._format_error(f"failed to open tab: {self._error_message(e)}")

        tab_id = f"t{self._next_tab_seq}"
        self._next_tab_seq += 1
        page.on("popup", lambda p, tid=tab_id: self._on_popup_sync(tid, p))  # type: ignore[call-overload]
        page.on("dialog", lambda d, tid=tab_id: self._on_dialog_sync(tid, d))  # type: ignore[call-overload]

        state = _TabState(tab_id=tab_id, page=page, last_touched_turn=self._turn_counter)
        self._tabs[tab_id] = state
        return state, None

    async def _discard_tab(self, state: "_TabState") -> None:
        """Roll back a tab created by ``_open_new_tab`` after a load failure."""
        self._tabs.pop(state.tab_id, None)
        try:
            await state.page.close()
        except Exception:
            pass
        if self._manager is not None:
            await self._manager.release_page()

    async def browser_click(self, tab: str, ref: str) -> str:
        """Click an interactive element on a specific tab.

        Downloads are disabled — clicking a download link succeeds but
        produces no page change; don't retry the same ref.

        Args:
            tab: The id of the tab to act on, e.g. ``"t1"`` (from a previous response).
            ref: The ref string of the target element, e.g. ``"e15"``. Must come
                from the tab's MOST RECENT response — refs are per-snapshot.
        """
        self._metrics.num_clicks += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        async with state.op_lock:
            try:
                locator = self._resolve_ref(state, ref)
                await self._click_with_overlay_fallback(locator)
                await self._settle(state)
            except _RefError as e:
                return self._format_error(str(e))
            except Exception as e:
                return self._format_error(f"click failed: {self._error_message(e)}")
            state.last_touched_turn = self._turn_counter
            return await format_tab_response(state)

    async def _click_with_overlay_fallback(self, locator: "Locator") -> None:
        """Click ``locator``, routing around aria-hidden overlays (Material
        ripple, MUI/Radix composite wrappers) that hit-test on top of the
        target. Pre-check via ``elementFromPoint``: if the topmost element
        is the target, an ancestor, or a descendant, do a normal Playwright
        click; otherwise deliver the click via ``el.click()`` in-page to
        bypass hit-testing without paying the ~10s retry-then-timeout.
        Reactive fallback covers the rare check-vs-click race.
        """
        try:
            occluded = await locator.evaluate(
                """el => {
                    const r = el.getBoundingClientRect();
                    if (!r.width || !r.height) return false;
                    const x = r.left + r.width / 2;
                    const y = r.top + r.height / 2;
                    const top = document.elementFromPoint(x, y);
                    if (!top || top === el || el.contains(top) || top.contains(el)) return false;
                    return true;
                }"""
            )
        except Exception:
            occluded = False
        if occluded:
            await locator.evaluate("el => el.click()")
            self._metrics.num_clicks_dispatched_through_overlay += 1
            return
        try:
            await locator.click(timeout=_SETTLE_TIMEOUT_MS)
        except Exception as e:
            if "intercepts pointer events" not in str(e):
                raise
            # Race: overlay appeared between pre-check and click.
            await locator.evaluate("el => el.click()")
            self._metrics.num_clicks_dispatched_through_overlay += 1

    async def browser_type(
        self, tab: str, ref: str, text: str, submit: bool = False, slowly: bool = False
    ) -> str:
        """Type text into an editable element on a specific tab.

        Args:
            tab: The id of the tab to act on, e.g. ``"t1"``.
            ref: The ref string of the target element, e.g. ``"e15"``. Must come
                from the tab's MOST RECENT response — refs are per-snapshot.
            text: The text to type. Replaces existing content.
            submit: If True, press Enter after typing. Without submit the
                response is a short ack since the page state hasn't changed
                beyond the input field's value (which the agent already knows).
            slowly: If True, type one character at a time (simulating real
                keystrokes) instead of setting the value in one shot. Slower,
                but fires the per-key handlers some autocomplete/combobox
                widgets need to populate their suggestion dropdown. Try this
                when a normal type leaves the field's options unpopulated.
        """
        self._metrics.num_types += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        async with state.op_lock:
            try:
                locator = self._resolve_ref(state, ref)
                if slowly:
                    # Clear via the fast path, then emit real keystrokes so
                    # key-driven suggestion handlers fire.
                    await locator.fill("", timeout=_SETTLE_TIMEOUT_MS)
                    await locator.press_sequentially(text, timeout=_SETTLE_TIMEOUT_MS)
                else:
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
                # Two outcomes from the wait:
                # - Options surfaced (autocomplete dropdown appeared): the DOM
                #   shape changed, so prior refs are invalid anyway. Return a
                #   fresh full snapshot so the agent has a coherent ref space
                #   for the suggestions plus the rest of the page.
                # - No options: typing into a plain input doesn't reshape the
                #   ARIA tree, so the pre-type snapshot stays authoritative.
                #   Skip the re-snapshot and return a cheap ack; the agent's
                #   existing refs keep resolving.
                try:
                    await state.page.wait_for_selector(
                        "[role=option]", timeout=_AUTOCOMPLETE_WAIT_MS
                    )
                except Exception:
                    return f"[tab={tab}] typed into ref={ref}"
                # ``wait_for_selector`` returns on the first option attaching to
                # the DOM — the rest of the dropdown is still rendering and
                # accessible names haven't been computed. Apply the same
                # networkidle + post-load settle as navigation/click so the
                # snapshot isn't taken mid-hydration.
                await self._settle(state)
                return await format_tab_response(state)
            return await format_tab_response(state)

    async def browser_scroll(self, tab: str, direction: Literal["up", "down", "top", "bottom"]) -> str:
        """Scroll a specific tab.

        Args:
            tab: The id of the tab to scroll, e.g. ``"t1"``.
            direction: One of ``"up"``, ``"down"``, ``"top"``, ``"bottom"``.
        """
        self._metrics.num_scrolls += 1
        if direction not in ("up", "down", "top", "bottom"):
            return self._format_error(f"invalid direction {direction!r}; expected up/down/top/bottom")
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

        Use this whenever a previous action replaced the tab's page and you
        still need the prior content. Triggers include:

        - ``browser_navigate`` with ``tab=<id>`` (explicit in-place navigation).
        - ``browser_click`` on a link, form submit, or JS-driven nav element.
        - ``browser_type`` with ``submit=True`` causing a form post or search redirect.

        A page replacement discards the prior page's DOM, JS state, and text
        content entirely; ``browser_back`` is the only way to recover it without
        re-navigating to the URL by hand.

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
                await asyncio.sleep(_POST_LOAD_SETTLE_MS / 1000)
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
                await state.page.keyboard.press(_normalize_key(key))
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
            ref: The ref string of the target element, e.g. ``"e15"``. Must come
                from the tab's MOST RECENT response — refs are per-snapshot.
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

    async def browser_wait(
        self,
        tab: str,
        seconds: float = 3.0,
        text: str | None = None,
        text_gone: str | None = None,
    ) -> str:
        """Wait for a condition (or a fixed time), then re-snapshot the tab.

        Prefer ``text`` / ``text_gone`` over a fixed sleep — they return as
        soon as the condition holds. Reach for ``seconds`` when no stable
        text exists to key off.

        Reach for this when the last snapshot looks under-hydrated: many
        ``button [ref=eXXX]`` without names, bare ``[]`` icons, bare ``#`` /
        ``##`` headings, or stripped combobox labels. 1-3s is usually enough.
        Don't call after every action — nav/mutation tools already apply a
        small post-load settle.

        Args:
            tab: The id of the tab to re-snapshot afterward, e.g. ``"t1"``.
            seconds: Fixed sleep when neither ``text`` nor ``text_gone`` is
                given; otherwise the timeout.
            text: Wait until this text appears.
            text_gone: Wait until this text disappears.
        """
        self._metrics.num_waits += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        seconds = max(0.0, seconds)
        async with state.op_lock:
            try:
                if text is not None:
                    await state.page.get_by_text(text).first.wait_for(
                        state="visible", timeout=seconds * 1000
                    )
                elif text_gone is not None:
                    await state.page.get_by_text(text_gone).first.wait_for(
                        state="hidden", timeout=seconds * 1000
                    )
                else:
                    await asyncio.sleep(seconds)
            except Exception:
                # Timed out waiting for the condition — fall through and
                # snapshot anyway so the agent sees the current state.
                pass
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
            if self._manager is not None:
                await self._manager.release_page()
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
            if self._manager is not None:
                await self._manager.release_page()
        if self._owned_context is not None:
            try:
                await self._owned_context.close()
            except Exception:
                pass
            self._owned_context = None

    # === Pydantic-AI integration =============================================

    def as_pydantic_ai_tools(self) -> list[Tool]:
        """Return this tool's browse actions as pydantic-ai ``Tool`` objects.

        All actions share this instance's tab/snapshot state. Splat into
        ``Agent(tools=[..., *web_browser.as_pydantic_ai_tools()])`` and pair
        with ``capabilities=[web_browser.lifecycle_capability()]`` so idle
        tabs are cleaned up at turn boundaries.
        """
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

    def lifecycle_capability(self) -> "Hooks[None]":
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
        state.popup_notice = f"[note: previous action on tab {tab_id} opened a popup; this tab is now {popup_url}]"
        self._metrics.num_popups_adopted += 1
        if old_page is not None and old_page is not popup:
            try:
                await old_page.close()
            except Exception:
                pass
        popup.on("popup", lambda p, tid=tab_id: self._on_popup_sync(tid, p))  # type: ignore[call-overload]
        popup.on("dialog", lambda d, tid=tab_id: self._on_dialog_sync(tid, d))  # type: ignore[call-overload]

    def _on_dialog_sync(self, tab_id: str, dialog: Any) -> None:
        """Sync wrapper that schedules the async dialog handler."""
        asyncio.create_task(self._on_dialog(tab_id, dialog))

    async def _on_dialog(self, tab_id: str, dialog: Any) -> None:
        """Auto-dismiss a JS dialog so it doesn't block the tab.

        Modal ``alert()`` / ``confirm()`` / ``prompt()`` / ``beforeunload``
        block all interactions until handled. Playwright does NOT auto-dismiss
        by default. Policy: accept alert/confirm/beforeunload (safer for
        automation — proceed past the dialog) and dismiss prompt (we can't
        supply an answer). The dialog's type and message are recorded as a
        notice on the tab so the agent sees that something fired.
        """
        dialog_type = getattr(dialog, "type", "alert")
        message = getattr(dialog, "message", "")
        try:
            if dialog_type == "prompt":
                await dialog.dismiss()
                action = "dismissed (Cancel)"
            else:
                await dialog.accept()
                action = "accepted (OK)"
        except Exception:
            return
        state = self._tabs.get(tab_id)
        if state is not None:
            state.popup_notice = (
                f"[note: {dialog_type} dialog on tab {tab_id} auto-{action}; "
                f"message: {message!r}]"
            )

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
        await asyncio.sleep(_POST_LOAD_SETTLE_MS / 1000)

    def _resolve_ref(self, state: _TabState, ref: str) -> "Locator":
        if state.last_snapshot is None:
            raise _RefError(f"page {state.tab_id}: no snapshot available; call any action first")
        if ref not in state.last_snapshot.refs:
            available = state.last_snapshot.refs
            shown = available[:30]
            suffix = f" (+ {len(available) - 30} more)" if len(available) > 30 else ""
            hints: list[str] = []
            if not _REF_PATTERN.match(ref):
                hints.append(f"{ref!r} is not in the expected ``eN`` form (e.g. ``e15``)")
            hints.append(
                "refs are per-snapshot — only those from this tab's MOST RECENT response are "
                "valid. If you're reusing one from an earlier response, re-read the latest "
                "snapshot and pick a ref from there"
            )
            raise _RefError(
                f"page {state.tab_id}: unknown ref {ref!r}. "
                + ". ".join(hints)
                + f". Available refs: {shown}{suffix}"
            )
        return state.page.locator(f"aria-ref={ref}")

    def _format_error(self, msg: str) -> str:
        self._metrics.num_errors += 1
        return f"(error: {msg})"

    @staticmethod
    def _error_message(e: Exception) -> str:
        msg = str(e).strip()
        return msg or e.__class__.__name__
