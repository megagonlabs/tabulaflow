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
placed right after each link, button, or input.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel
from pydantic_ai import Tool

# BaseLoader (not Safe/FullLoader): aria scalars like ``=`` and ``~`` would
# trigger YAML 1.1 special-tag resolution under SafeLoader (``ConstructorError``).
# BaseLoader keeps every scalar as a string — which is exactly what we want.
try:  # fast C loader when available; falls back to the pure-Python loader
    from yaml import CBaseLoader as _YamlLoader
except ImportError:  # pragma: no cover
    from yaml import BaseLoader as _YamlLoader  # type: ignore[assignment]

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
# render their JS-injected content. Capped because some sites (Google Flights,
# dashboards with continuous polling) never reach networkidle within reason.
# 10s comfortably covers most modern SPAs (React apps with API calls, news
# sites, social feeds) while bounding worst-case latency on streaming pages.
_NETWORKIDLE_WAIT_MS = 10_000

# Tighter budget for in-site navigations (click/type that stays on same host).
# Same-domain navs typically reuse cached CSS/JS and settle faster — we don't
# need the full SPA-rendering budget. Borrowed from browser-use's heuristic.
_NETWORKIDLE_WAIT_MS_SAME_DOMAIN = 3_000

# How long a no-submit ``browser_type`` waits for an autocomplete dropdown to
# appear before snapshotting. Short on purpose: when typing surfaces options we
# return quickly; when it doesn't (a plain text field) we only pay this once.
_AUTOCOMPLETE_WAIT_MS = 1_500


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_REF_PATTERN = re.compile(r"\[ref=(e\d+)\]")

# A node header within the aria-snapshot YAML, e.g. `combobox "menu" [expanded]
# [ref=e7]`. Captures the role, optional quoted name, and the trailing bracketed
# attributes (`[ref=…]`, `[checked]`, `[cursor=pointer]`, …) as one blob, which
# we mine for the ref and state flags below.
_HEADER_PATTERN = re.compile(
    r'^(?P<role>[\w-]+)(?:\s+"(?P<name>.*?)")?(?P<attrs>(?:\s*\[[^\]]*\])*)\s*$'
)
# State flags Playwright emits as `[flag]` (or `[flag=value]`) — the element's
# interactable state. We surface these; `[ref=…]`/`[active]`/`[level=…]`/
# `[cursor=…]` are deliberately excluded (handled elsewhere / low value).
_STATE_FLAG_PATTERN = re.compile(
    r"\[(?P<flag>checked|disabled|selected|expanded|pressed|readonly)(?:=(?P<val>[\w-]+))?\]"
)
# Per-line role/name/ref extractor, used only by the fallback path when the
# whole snapshot fails to parse as YAML.
_FALLBACK_LINE_PATTERN = re.compile(
    r'-\s+(?P<role>[\w-]+)(?:\s+"(?P<name>[^"]*)")?[^\n]*?\[ref=(?P<ref>e\d+)\]'
)
# Cap on how many native-<select> option labels to surface in the snapshot,
# so a long dropdown (countries, timezones) can't bloat the token budget.
_MAX_NATIVE_OPTIONS = 15

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

# Roles rendered transparently — they have no markdown representation of their
# own, we just emit their children. Most accessibility-tree noise lives here.
_TRANSPARENT_ROLES: frozenset[str] = frozenset(
    {
        "generic", "region", "main", "navigation", "banner", "contentinfo",
        "article", "section", "group", "complementary",
        "dialog", "alertdialog", "tabpanel",
        "tooltip", "status", "alert", "progressbar",
    }
)

# Grouping roles — represent a logical group of controls/items. We always
# bullet their meaningful children (the flight-search form, search boxes,
# tab strips, menus) so the controls don't collapse onto one inline run.
_GROUPING_ROLES: frozenset[str] = frozenset(
    {"form", "search", "tablist", "menubar", "menu"}
)

# Heading depth: aria emits ``[level=N]`` for ``<h1>``…``<h6>``.
_LEVEL_PATTERN = re.compile(r"\[level=(\d+)\]")


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


# ---------------------------------------------------------------------------
# Snapshot: interactive elements + clean markdown
#
# Two complementary views of the page:
#   1. Filtered list of interactive elements (with refs for click/type)
#   2. Clean markdown content of the page (for reading)
#
# Both views derive from a single ``aria_snapshot(mode="ai")`` walk: refs
# resolve via the ``aria-ref=eN`` locator, and the markdown is rendered from
# the same YAML tree so refs land inline by construction (no HTML pass).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InteractiveElement:
    ref: str
    role: str
    name: str
    href: str | None = None
    parent_context: tuple[str, str] | None = None  # (role, name) of nearest named ancestor
    native_select: bool = False  # combobox backed by a native <select> (use browser_select)
    native_options: tuple[str, ...] = ()  # option labels of a native <select> (capped)
    state: tuple[str, ...] = ()  # interactable state flags, e.g. ("checked", "disabled")
    value: str | None = None  # current value of a textbox/combobox/slider


@dataclass
class PageSnapshot:
    url: str
    title: str
    interactive_elements: list[InteractiveElement] = field(default_factory=list)
    markdown_content: str = ""
    refs: set[str] = field(default_factory=set)


# aria_snapshot(mode="ai") is valid YAML, so PyYAML owns hierarchy/nesting/
# escaping; we only parse each node's header string.
def _split_node(node: Any) -> tuple[str | None, Any]:
    """Return ``(header, body)`` for a YAML aria node (str leaf or 1-key dict)."""
    if isinstance(node, str):
        return node, None
    if isinstance(node, dict) and len(node) == 1:
        (header, body), = node.items()
        return header, body
    return None, None


def _parse_header(header: str) -> tuple[str, str, str | None, tuple[str, ...], bool] | None:
    """Parse ``role "name" [attr]…`` into (role, name, ref, state-flags, clickable).

    ``clickable`` reflects Playwright's ``[cursor=pointer]`` hint — used to
    recover non-semantic but clickable ``generic`` elements.
    """
    m = _HEADER_PATTERN.match(header.strip())
    if m is None:
        return None
    attrs = m.group("attrs") or ""
    ref_m = _REF_PATTERN.search(attrs)
    state = tuple(
        f.group("flag") + (f"={f.group('val')}" if f.group("val") else "")
        for f in _STATE_FLAG_PATTERN.finditer(attrs)
    )
    clickable = "[cursor=pointer]" in attrs
    return m.group("role"), m.group("name") or "", (ref_m.group(1) if ref_m else None), state, clickable


def _native_select_options(children: list[Any]) -> list[str]:
    """Labels of ref-less ``option`` descendants — the tell for a native <select>.

    A native <select> nests its <option>s (without refs) even when collapsed;
    a collapsed ARIA combobox has no children and an expanded one's options sit
    in a sibling listbox with refs.
    """
    out: list[str] = []

    def visit(nodes: list[Any]) -> None:
        for node in nodes:
            header, body = _split_node(node)
            if header is None:
                continue
            parsed = _parse_header(header)
            if parsed is not None:
                role, name, ref, _, _ = parsed
                if role == "option" and ref is None:
                    out.append(name)
            if isinstance(body, list):  # descend into <optgroup>
                visit(body)

    visit(children)
    return out


def _has_click_target(nodes: list[Any]) -> bool:
    """True if the subtree holds an interactable element or clickable generic.

    Used to skip clickable wrapper ``generic``s (which merely contain a real
    button/link) and promote only the innermost clickable target.
    """
    for node in nodes:
        header, body = _split_node(node)
        if header is not None:
            parsed = _parse_header(header)
            if parsed is not None:
                role, _, ref, _, clickable = parsed
                if (role in _INTERACTIVE_ROLES and ref is not None) or (
                    role == "generic" and clickable
                ):
                    return True
        if isinstance(body, list) and _has_click_target(body):
            return True
    return False


def parse_interactive_elements(aria_yaml: str) -> list[InteractiveElement]:
    """Walk the aria-snapshot YAML, capturing each interactive element's value,
    state flags, link href, native-<select> options, and nearest context-bearing
    ancestor/preceding-sibling. Falls back to a minimal ref/role/name scan if the
    YAML can't be parsed.
    """
    try:
        tree = yaml.load(aria_yaml, Loader=_YamlLoader)
    except yaml.YAMLError as e:
        logger.debug("aria YAML parse failed, using fallback: %s", e)
        return _parse_interactive_elements_fallback(aria_yaml)
    if not isinstance(tree, list):
        return []

    elements: list[InteractiveElement] = []
    # Context-bearing nodes in scope: nearest one at depth <= mine wins.
    context_stack: list[tuple[int, str, str]] = []

    def walk(node: Any, depth: int) -> None:
        header, body = _split_node(node)
        if header is None:
            return
        parsed = _parse_header(header)
        if parsed is None:
            return
        role, name, ref, state, clickable = parsed
        children = body if isinstance(body, list) else []
        value = str(body) if isinstance(body, str | int | float) else None

        while context_stack and context_stack[-1][0] > depth:
            context_stack.pop()
        if role in _CONTEXT_ROLES and name:
            context_stack.append((depth, role, name))

        # Promote a non-semantic `generic` only when it's clickable and is the
        # innermost target (no interactive/clickable descendant) — skips the
        # wrapper divs that merely contain a real button/link.
        promote_generic = (
            role == "generic"
            and clickable
            and ref is not None
            and not _has_click_target(children)
        )
        if (role in _INTERACTIVE_ROLES or promote_generic) and ref is not None:
            href: str | None = None
            if role == "link":
                for child in children:
                    c_header, c_body = _split_node(child)
                    if c_header is not None and c_header.strip().startswith("/url"):
                        href = str(c_body).strip() if c_body is not None else None
                        break

            opts = _native_select_options(children) if role == "combobox" else []
            ctx = (context_stack[-1][1], context_stack[-1][2]) if context_stack else None

            elements.append(
                InteractiveElement(
                    ref=ref,
                    role=role,
                    name=name,
                    href=href,
                    parent_context=ctx,
                    native_select=bool(opts),
                    native_options=tuple(opts[:_MAX_NATIVE_OPTIONS]),
                    state=(*state, "clickable") if promote_generic else state,
                    value=value,
                )
            )

        for child in children:
            walk(child, depth + 1)

    for node in tree:
        walk(node, 0)
    return elements


def _parse_interactive_elements_fallback(aria_yaml: str) -> list[InteractiveElement]:
    """Degraded ref/role/name extraction if the YAML can't be parsed."""
    elements: list[InteractiveElement] = []
    for line in aria_yaml.split("\n"):
        m = _FALLBACK_LINE_PATTERN.match(line)
        if m is None or m.group("role") not in _INTERACTIVE_ROLES:
            continue
        elements.append(
            InteractiveElement(ref=m.group("ref"), role=m.group("role"), name=m.group("name") or "")
        )
    return elements


# -- aria → markdown renderer (Phase 1: core prose roles) ------------------
# Single walk over the same YAML tree we already parse for interactive
# elements. Refs inline by construction — no text-matching kludge. Phase 1
# covers headings, paragraphs, links, buttons, lists, and transparent
# containers; later phases add tables, code blocks, images, and inline form
# controls.


def render_aria_markdown(aria_yaml: str) -> str:
    """Render an aria-snapshot YAML string as markdown with refs inlined."""
    try:
        tree = yaml.load(aria_yaml, Loader=_YamlLoader)
    except yaml.YAMLError:
        return ""
    if not isinstance(tree, list):
        return ""
    # Top-level defaults to flow=True (prose-friendly): paragraphs and headings
    # emit their own markdown, and the page-wrapping generics inline normally.
    # Lower contexts (notably listitem children) switch to flow=False so a
    # multi-child generic fans out as nested bullets instead of producing a wall.
    text = "".join(_render_md_node(n, depth=0, flow=True) for n in tree)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# Form-control roles render inline as ``role "name" = "value" [flag] [ref=eN]``.
_FORM_CONTROL_ROLES: frozenset[str] = frozenset({
    "textbox", "searchbox", "combobox", "checkbox", "radio",
    "switch", "slider", "spinbutton", "tab",
})


def _render_md_node(node: Any, depth: int = 0, flow: bool = False) -> str:
    """Render one aria YAML node as a markdown fragment.

    ``flow=True`` means we're inside a prose flow (paragraph, heading, link,
    listitem text, cell). Inline atoms concatenate. ``flow=False`` (top level
    or inside a structural container) means a transparent container with
    multiple children fans out as nested bullets — this is what tames the
    SPA-divs-deep wall on pages like Google Flights.
    """
    header, body = _split_node(node)
    if header is None or header.startswith("/url"):
        return ""
    parsed = _parse_header(header)
    if parsed is None:
        return ""
    role, name, ref, state, clickable = parsed
    children = body if isinstance(body, list) else []
    value = str(body) if isinstance(body, str | int | float) else None
    ref_tag = f" [ref={ref}]" if ref else ""

    # ---- Block-level markdown forms (always emit their own form). ----
    if role == "heading":
        m = _LEVEL_PATTERN.search(header)
        level = max(1, min(int(m.group(1)) if m else 2, 6))
        content = _kids_md(children, depth, flow=True).strip() or name
        return f"\n\n{'#' * level} {content}\n\n"
    if role == "paragraph":
        return f"\n\n{_kids_md(children, depth, flow=True).strip()}\n\n"
    if role == "code":
        body_md = name or value or _kids_md(children, depth, flow=True).strip()
        if "\n" in body_md or len(body_md) > 80:
            return f"\n\n```\n{body_md}\n```\n\n"
        return f"`{body_md}`"
    if role == "separator":
        return "\n\n---\n\n"
    if role in ("table", "grid"):
        if _is_data_table(children):
            return f"\n\n{_render_md_table(children)}\n\n"
        return _bullet_block(value, children, depth, ref_tag)
    if role == "list":
        return f"\n\n{_kids_md(children, depth, flow=False).strip()}\n\n"
    if role == "listitem":
        return _render_listitem(value, children, depth, ref_tag)

    # ---- Inline atoms (return inline text). ----
    if role == "text":
        return value or ""
    if role == "link":
        href = _find_url_child(children)
        # Drop aria-only ``<a>`` elements: no href and no ref means the link
        # exists solely as a screen-reader description, with no navigation
        # target or interactable handle. Be visible-content-centric.
        if not href and not ref:
            return ""
        body_md = name or _kids_md(
            [c for c in children if not _is_url_node(c)], depth, flow=True
        ).strip()
        return f"[{body_md}]({href}){ref_tag}" if href else f"[{body_md}]{ref_tag}"
    if role == "button":
        body_md = name or _kids_md(children, depth, flow=True).strip()
        return f'button "{body_md}"{ref_tag}' if body_md else f"button{ref_tag}"
    if role in _FORM_CONTROL_ROLES:
        return _render_md_form_control(role, name, value, state, ref_tag, children)
    if role == "img":
        return f"![{name}](){ref_tag}" if name else ""

    # ---- Layout-table parts standalone. ----
    if role in ("row", "rowgroup", "cell", "gridcell", "columnheader", "rowheader"):
        if flow:
            leading = (value + " ") if value else ""
            return leading + _kids_md(children, depth, flow=True)
        return _bullet_block(value, children, depth, ref_tag)

    # ---- Clickable generic promotion (inline marker). ----
    if (
        role == "generic"
        and clickable
        and ref is not None
        and not _has_click_target(children)
    ):
        inner = ((value + " ") if value else "") + _kids_md(children, depth, flow=True).strip()
        inner_text = inner.strip()
        return f'clickable "{inner_text}"{ref_tag}' if inner_text else f"clickable{ref_tag}"

    # ---- Grouping roles (form/search/tablist/menu): flatten + paragraph. ----
    if role in _GROUPING_ROLES:
        meaningful = _meaningful_children(children)
        if len(meaningful) <= 1:
            leading = (value + " ") if value else ""
            return leading + _kids_md(children, depth, flow=flow)
        # Flatten transparent descendants into a flat list of leaves, then
        # emit each as its own paragraph. Avoids indent inversion from
        # arbitrary DOM-wrapper depth (Google Flights' nested form generics).
        leaves: list[str] = []
        _flatten_to_leaves(children, depth, leaves)
        if not leaves:
            return ""
        return "\n\n" + "\n\n".join(leaves) + "\n\n"

    # ---- Transparent containers. ----
    if role in _TRANSPARENT_ROLES:
        # A bare value-bearing transparent generic is almost always an aria-
        # labelled informational ``<div>`` — drop its ref unless it's actually
        # clickable (cursor=pointer wrappers can still carry a real handler).
        effective_ref = ref_tag if (clickable or role != "generic") else ""
        if flow:
            leading = (value + " ") if value else ""
            return leading + _kids_md(children, depth, flow=True)
        return _bullet_block(value, children, depth, effective_ref)

    # Unknown role fallback: inline-transparent.
    leading = (value + " ") if value else ""
    return leading + _kids_md(children, depth, flow=flow)


def _kids_md(children: list[Any], depth: int, flow: bool = False) -> str:
    return "".join(_render_md_node(c, depth, flow=flow) for c in children)


def _meaningful_children(children: list[Any]) -> list[Any]:
    """Drop empty/skippable nodes (``/url`` annotations) before bulleting."""
    out: list[Any] = []
    for c in children:
        h, _ = _split_node(c)
        if h is None or h.strip().startswith("/url"):
            continue
        out.append(c)
    return out


def _bullet_block(
    value: str | None, children: list[Any], depth: int, ref_tag: str
) -> str:
    """Render a transparent/structural container as nested bullets.

    Collapses single-child wrappers so deep ``generic > generic > generic``
    chains don't pile up indentation. Each meaningful child becomes a bullet
    at ``depth``; descendants recurse at ``depth + 1`` in flow mode (their own
    multi-child generics will fan out further on demand).
    """
    meaningful = _meaningful_children(children)
    if not value and len(meaningful) == 0:
        return ref_tag.strip() if ref_tag else ""
    if not value and len(meaningful) == 1:
        return _render_md_node(meaningful[0], depth, flow=False)
    indent = "  " * depth
    lines: list[str] = []
    if value:
        lines.append(f"{indent}- {value}{ref_tag if not meaningful else ''}")
    for c in meaningful:
        # Render at depth+1 in bullet mode so the child can produce its own
        # nested structure. If it already returns bullet lines (starts with
        # ``- ``), use them as-is at depth+1 — don't double-wrap. If it
        # returns inline content, wrap it as a single bullet at ``depth``.
        cm = _render_md_node(c, depth + 1, flow=False).strip("\n")
        if not cm.strip():
            continue
        first_nonblank = cm.lstrip().split("\n", 1)[0]
        if first_nonblank.startswith("- "):
            lines.append(cm)
        else:
            first, _, rest = cm.partition("\n")
            lines.append(f"{indent}- {first}" + (f"\n{rest}" if rest else ""))
    return "\n" + "\n".join(lines) + "\n"


def _render_listitem(
    value: str | None, children: list[Any], depth: int, ref_tag: str
) -> str:
    """Render a listitem at ``depth``, with leaves at ``depth+1`` as bullets.

    Transparent-generic descendants of the listitem are flattened into a single
    level of bullets — keeps SPA UIs (flight rows, search results) readable
    without producing arbitrarily deep nesting. Nested ``list``/``table``
    children stop the flattening so real sub-lists and tables keep structure.
    """
    indent = "  " * depth
    sub_indent = "  " * (depth + 1)
    leaves: list[str] = []
    if value:
        leaves.append(value)
    _flatten_to_leaves(children, depth + 1, leaves)
    if not leaves:
        return f"\n{indent}-{ref_tag}" if ref_tag.strip() else ""
    # First leaf on the bullet line; remainder as nested bullets at depth+1.
    head_first, _, head_rest = leaves[0].partition("\n")
    out = f"\n{indent}- {head_first}" + (ref_tag if len(leaves) == 1 else "")
    if head_rest:
        out += "\n" + head_rest
    for leaf in leaves[1:]:
        first, _, rest = leaf.partition("\n")
        out += f"\n{sub_indent}- {first}"
        if rest:
            out += "\n" + rest
    return out


def _flatten_to_leaves(nodes: list[Any], depth: int, out: list[str]) -> None:
    """Walk transparent containers, collecting renderable leaves into ``out``.

    A "leaf" is anything the listitem should show as one bullet:
      * a transparent container's scalar value — ref kept only when the node
        is clickable (cursor=pointer); aria-labelled informational divs lose
        their refs since they're not actionable,
      * any non-transparent node (link, button, form control, list, table,
        heading, paragraph, code, image, etc.), rendered via the normal walk.
    Lists/tables stop the flattening — they recurse via ``_render_md_node``
    so their structure is preserved as nested markdown.
    """
    for c in nodes:
        h, b = _split_node(c)
        if h is None or h.strip().startswith("/url"):
            continue
        parsed = _parse_header(h)
        if parsed is None:
            continue
        role, _, ref, _, clickable = parsed
        kids = b if isinstance(b, list) else []
        value = b if isinstance(b, str) else None
        if role in _TRANSPARENT_ROLES:
            if value:
                tag = f" [ref={ref}]" if ref and clickable else ""
                out.append(value + tag)
            if kids:
                _flatten_to_leaves(kids, depth, out)
            continue
        # Non-transparent: render normally (could be link/button/list/etc.)
        cm = _render_md_node(c, depth, flow=True).strip()
        if cm:
            out.append(cm)


def _is_data_table(children: list[Any]) -> bool:
    rows = _flatten_rows(children)
    if not rows or any(_subtree_contains_role(r, ("table", "grid")) for r in rows):
        return False
    return any(len(_row_cells(r)) >= 2 for r in rows)


def _subtree_contains_role(node: Any, roles: tuple[str, ...]) -> bool:
    header, body = _split_node(node)
    if header is not None:
        parsed = _parse_header(header)
        if parsed is not None and parsed[0] in roles:
            return True
    if isinstance(body, list):
        return any(_subtree_contains_role(c, roles) for c in body)
    return False


def _render_md_form_control(
    role: str, name: str, value: str | None, state: tuple[str, ...],
    ref_tag: str, children: list[Any],
) -> str:
    """Render a form control inline as ``role "name" = "value" [flag] [ref=eN]``."""
    parts: list[str] = [role]
    if name:
        parts.append(f'"{name}"')
    if value is not None:
        parts.append(f'= "{value}"')
    elif children:
        kids = _kids_md(children, depth=0, flow=True).strip()
        if kids:
            parts.append(f'= "{kids}"')
    for flag in state:
        parts.append(f"[{flag}]")
    if ref_tag:
        parts.append(ref_tag.strip())
    return " ".join(parts)


def _render_md_table(children: list[Any]) -> str:
    """Render a table's row children as a GFM pipe table."""
    rows = _flatten_rows(children)
    if not rows:
        return ""
    # Find a header row: prefer the first row containing ``columnheader``s.
    header_idx = next(
        (i for i, r in enumerate(rows) if _row_has_role(r, "columnheader")),
        0,
    )
    header_cells = _row_cells(rows[header_idx])
    body_rows = rows[:header_idx] + rows[header_idx + 1:]
    width = max((len(header_cells), *[len(_row_cells(r)) for r in body_rows]))
    header = _pipe_join(header_cells, width)
    sep = "| " + " | ".join(["---"] * width) + " |"
    body = "\n".join(_pipe_join(_row_cells(r), width) for r in body_rows)
    return f"{header}\n{sep}\n{body}" if body else f"{header}\n{sep}"


def _flatten_rows(nodes: list[Any]) -> list[Any]:
    """Collect ``row`` nodes from a possibly-nested ``rowgroup`` structure."""
    out: list[Any] = []
    for n in nodes:
        h, b = _split_node(n)
        if h is None:
            continue
        parsed = _parse_header(h)
        if parsed is None:
            continue
        role = parsed[0]
        if role == "row":
            out.append(n)
        elif role in ("rowgroup", "table", "grid") and isinstance(b, list):
            out.extend(_flatten_rows(b))
    return out


def _row_cells(row_node: Any) -> list[str]:
    _h, b = _split_node(row_node)
    if not isinstance(b, list):
        return []
    cells: list[str] = []
    for c in b:
        ch, cb = _split_node(c)
        if ch is None:
            continue
        p = _parse_header(ch)
        if p is None:
            continue
        if p[0] in ("cell", "gridcell", "columnheader", "rowheader"):
            # Prefer rendered children so nested link/button refs survive into
            # the table; fall back to the cell's accessible name / scalar.
            kids = cb if isinstance(cb, list) else []
            kids_text = _kids_md(kids, depth=0, flow=True).strip()
            text = kids_text or p[1] or (str(cb) if isinstance(cb, str) else "")
            ref = p[2]
            if ref and f"[ref={ref}]" not in text:
                text = f"{text} [ref={ref}]" if text else f"[ref={ref}]"
            # Sanitize pipe characters that would break the GFM table.
            cells.append(text.replace("|", "\\|").replace("\n", " "))
    return cells


def _row_has_role(row_node: Any, role: str) -> bool:
    _h, b = _split_node(row_node)
    if not isinstance(b, list):
        return False
    for c in b:
        ch, _ = _split_node(c)
        if ch is None:
            continue
        p = _parse_header(ch)
        if p is not None and p[0] == role:
            return True
    return False


def _pipe_join(cells: list[str], width: int) -> str:
    padded = cells + [""] * (width - len(cells))
    return "| " + " | ".join(c or " " for c in padded) + " |"


def _find_url_child(children: list[Any]) -> str | None:
    for c in children:
        h, b = _split_node(c)
        if h is not None and h.strip().startswith("/url") and b is not None:
            return str(b).strip()
    return None


def _is_url_node(node: Any) -> bool:
    h, _ = _split_node(node)
    return h is not None and h.strip().startswith("/url")


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
        if e.native_select:
            line += " (native <select>: use browser_select"
            if e.native_options:
                opts = ", ".join(f'"{o}"' for o in e.native_options)
                more = " …" if len(e.native_options) >= _MAX_NATIVE_OPTIONS else ""
                line += f" — options: {opts}{more}"
            line += ")"
        if e.name:
            line += f' "{e.name}"'
        if e.value is not None:
            line += f' = "{e.value}"'
        for flag in e.state:
            line += f" [{flag}]"
        if e.href:
            line += f" → {e.href}"
        if e.parent_context:
            ctx_role, ctx_name = e.parent_context
            line += f' (under: {ctx_role} "{ctx_name}")'
        out.append(line)
    return "\n".join(out)


async def take_snapshot(page: "Page") -> PageSnapshot:
    """Capture the current page as markdown + a flat interactive-elements list.

    Both views derive from a single aria-snapshot walk — refs are inline in
    the markdown by construction, no separate HTML pass.
    """
    try:
        aria_yaml = await page.aria_snapshot(mode="ai", timeout=_SETTLE_TIMEOUT_MS)
    except Exception as e:
        aria_yaml = ""
        logger.debug("aria_snapshot failed: %s", e)
    interactive = parse_interactive_elements(aria_yaml)
    refs = set(_REF_PATTERN.findall(aria_yaml))
    markdown = render_aria_markdown(aria_yaml)
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

    Takes a fresh snapshot — refs are already inline in the markdown via the
    aria-driven renderer, so we only list the interactive elements whose refs
    did not naturally surface in the page text (e.g., native-<select> options).
    Mutates ``state.last_snapshot`` and consumes any pending popup notice.
    """
    snapshot = await take_snapshot(state.page)
    state.last_snapshot = snapshot

    inlined_refs = set(_REF_PATTERN.findall(snapshot.markdown_content))
    remaining = [e for e in snapshot.interactive_elements if e.ref not in inlined_refs]

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
    parts.append(snapshot.markdown_content or "(no content extracted)")
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
            return self._format_error(f"unsupported URL scheme {parsed.scheme!r}; only http/https allowed")
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

        # Take a page permit from the process-wide budget before opening a tab.
        # First tab (we hold none) may block briefly for a slot; later tabs
        # fast-fail so a permit-holder never blocks while holding.
        manager = await self._ensure_manager()
        if not await manager.acquire_page(block=len(self._tabs) == 0):
            return self._format_error(
                "browser at capacity — close a tab or reduce parallelism, then retry"
            )

        try:
            ctx = await self._ensure_context()
            page = await ctx.new_page()
        except Exception as e:
            await manager.release_page()
            return self._format_error(f"failed to open tab: {self._error_message(e)}")

        page.on("popup", lambda p, tid=tab_id: self._on_popup_sync(tid, p))  # type: ignore[call-overload]

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
            await manager.release_page()
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

    async def browser_type(
        self, tab: str, ref: str, text: str, submit: bool = False, slowly: bool = False
    ) -> str:
        """Type text into an editable element on a specific tab.

        Args:
            tab: The id of the tab to act on, e.g. ``"t1"``.
            ref: The ref string of the input element, e.g. ``"e15"``.
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
                # Typing into a combobox/searchbox often surfaces an async
                # autocomplete dropdown — options the agent does NOT already
                # know and must click to commit a value. Briefly wait for any
                # such options, then re-snapshot so (a) the agent sees them and
                # (b) their refs become resolvable via last_snapshot. When no
                # dropdown appears we fall back to the cheap ack.
                try:
                    await state.page.wait_for_selector(
                        "[role=option]", timeout=_AUTOCOMPLETE_WAIT_MS
                    )
                except Exception:
                    pass
                snapshot = await take_snapshot(state.page)
                state.last_snapshot = snapshot
                options = [e for e in snapshot.interactive_elements if e.role == "option"]
                if options:
                    return (
                        f"[tab={tab}] typed into ref={ref}\n\n"
                        f"# Suggestions\n{render_interactive_elements(options)}"
                    )
                return f"[tab={tab}] typed into ref={ref}"
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

    async def browser_wait(
        self,
        tab: str,
        seconds: float = 3.0,
        text: str | None = None,
        text_gone: str | None = None,
    ) -> str:
        """Wait for a condition (or a fixed time), then re-snapshot the tab.

        Prefer ``text`` / ``text_gone`` over a fixed sleep: they return as
        soon as the condition holds, so they're both faster and more reliable
        than guessing how many ``seconds`` a render will take. Use ``seconds``
        alone only when there's no text to key off (e.g., a heavy dashboard
        that renders a few seconds after the network goes idle).

        Args:
            tab: The id of the tab to re-snapshot afterward, e.g. ``"t1"``.
            seconds: Fixed sleep, capped at 30s. Used when neither ``text`` nor
                ``text_gone`` is given; otherwise serves as the timeout for the
                text condition.
            text: If given, wait until this text appears on the page.
            text_gone: If given, wait until this text disappears from the page.
        """
        self._metrics.num_waits += 1
        state = self._tabs.get(tab)
        if state is None:
            return self._format_error(self._unknown_tab(tab))
        seconds = max(0.0, min(seconds, 30.0))
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
            raise _RefError(f"page {state.tab_id}: no snapshot available; call any action first")
        if ref not in state.last_snapshot.refs:
            available = sorted(state.last_snapshot.refs)
            raise _RefError(f"page {state.tab_id}: unknown ref {ref!r}. Available refs: {available[:30]}")
        return state.page.locator(f"aria-ref={ref}")

    def _format_error(self, msg: str) -> str:
        self._metrics.num_errors += 1
        return f"(error: {msg})"

    @staticmethod
    def _error_message(e: Exception) -> str:
        msg = str(e).strip()
        return msg or e.__class__.__name__
