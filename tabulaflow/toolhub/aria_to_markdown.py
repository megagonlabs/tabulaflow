"""Render a Playwright aria-snapshot YAML to LLM-friendly markdown.

Single walk over the YAML tree, dispatching per ARIA role.  Refs land
inline by construction; orphan descendants are anchored to their parent
via a swept-refs suffix.

Why markdown vs raw aria YAML
=============================

**Smaller and more readable than the raw tree.**  The same flight row
in raw aria (what playwright-mcp returns)::

    - listitem [ref=e354]:
      - generic [ref=e355]:
        - link "From 192 USD. 1 stop flight with Frontier..." [ref=e371]
        - generic [ref=e357] [cursor=pointer]:
          - generic "Departure: 11:59 PM" [ref=e366]: 11:59 PM
          - text: "-"
          - generic "Arrival: 12:32 PM" [ref=e369]: 12:32 PM
          - ... 10 more nested generics ...
        - button "Carbon emissions estimate..." [ref=e394]
        - button "Flight details..." [ref=e415]

rendered as markdown — the whole clickable row carries one ref (its own
"select" affordance); the informational time/airline spans drop theirs::

    - 11:59 PM - 12:32 PM +1 Frontier 9 hr 33 min SFO - EWR [ref=e357]
      - button "Carbon emissions estimate..." [ref=e394]
      - button "Flight details..." [ref=e415]

A 2.7x to 4.8x smaller than raw aria across real pages. Uses real markdown
(GitHub Markdown tables, nested bullets, prose flow) and drops aria-only
narrations so the snapshot matches what a sighted user sees.

A ``[ref=eN]`` marks an *actionable* element — a link, button, form control,
or clickable row/card. Non-clickable informational ``generic`` spans drop
their ref (a sighted user can't "click" a flight time either), so a ref always
means "you can act here" and rows stay uncluttered.

Field-level parsing
===================

Records stay machine-parseable at the boundary that matters: each record is one
bullet (``\\n-``) carrying its lone action ref. *Within* a record, fields are
separable only when the page itself marks them — a real ``<table>`` gives pipe
columns, and semantic ``<strong>``/``<em>`` gives ``**title** *authors*`` (see
``_INLINE_MARKUP``), both regex-splittable. Div-soup rows with no such markup
(flight summaries) are a single readable run — the LLM reads the fields; regex
finds the record and its ref. We deliberately do *not* stamp a ref on every
span to force a split: that overloads "actionable" and buries the real handle.

Locating an element
===================

Every interactive element renders as a self-contained, single-line
atom::

    [text](url) [ref=eN]            link
    button "name" [ref=eN]          button (also: clickable "text" [ref=eN])
    role "name" = "value" [ref=eN]  form controls (textbox/combobox/...)
    ![alt]() [ref=eN]               img
    option "name" [ref=eN]          live listbox option

Atoms may appear mid-line, so prefer the shape over line-anchored
greps::

    grep -oE '\\bbutton "[^"]*" \\[ref=e[0-9]+\\]' snapshot.md

When a snapshot has spilled to the workspace DuckDB (see
:class:`tabulaflow.toolhub.message_store.MessageStore`), the same atom shape
works as a SQL regex on ``_internal.messages.content``.  Use the inline
``(?i)`` flag for case-insensitive recall and alternation for multiple
keywords; the full atom comes back so the agent can verify the match::

    SELECT unnest(regexp_extract_all(content,
        '(?i)button "[^"]*(search|find|lookup)[^"]*" \\[ref=e[0-9]+\\]'
    )) AS atom
    FROM _internal.messages
    WHERE message_id = 'M42';
    -- atom -> 'button "Search" [ref=e25]'  (one row per match)

Refs are unique within a snapshot; find by name once, then act via ref.

Public API
==========

:func:`render_aria_markdown` is the main entry point: aria YAML string
in, markdown string out.

:func:`extract_refs` pulls every ``[ref=eN]`` id out of an arbitrary
string (markdown or raw YAML).
"""

from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import yaml


# ── YAML loader ──────────────────────────────────────────────────────────
# BaseLoader (not Safe/FullLoader): aria scalars like ``=`` and ``~`` would
# trigger YAML 1.1 special-tag resolution under SafeLoader (ConstructorError).
# BaseLoader keeps every scalar as a string — which is exactly what we want.
try:  # fast C loader when available
    from yaml import CBaseLoader as _YamlLoader
except ImportError:  # pragma: no cover
    from yaml import BaseLoader as _YamlLoader  # type: ignore[assignment]


# ── Constants ────────────────────────────────────────────────────────────

# Cap on native-<select> option labels surfaced in the snapshot, so a long
# dropdown (countries, timezones) can't bloat the token budget.
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
        "treeitem",
        "scrollbar",
    }
)

# Form-control roles render inline as ``role "name" = "value" [flag] [ref=eN]``.
_FORM_CONTROL_ROLES: frozenset[str] = frozenset(
    {
        "textbox",
        "searchbox",
        "combobox",
        "checkbox",
        "radio",
        "switch",
        "slider",
        "spinbutton",
        "tab",
    }
)

# Textual input form controls. When one of these is fully bare (no accessible
# name, no value, no interactive descendants), its rendered atom carries zero
# semantic info — the agent can't tell what the field is for, what's in it,
# or whether typing into it is destructive. Real screen readers also can't
# use these (WCAG 3.3.2 violation; NVDA/JAWS/VoiceOver announce role-only and
# users skip them). Bare textual inputs are dropped from the snapshot to
# avoid the agent targeting them speculatively from spatial proximity —
# notably the focus-trap demotion that Google Flights' "Where to?" combobox
# triggers, which made the agent type "New York" into the departure date.
# Checkboxes/radios/switches/tabs/sliders are NOT in this set: their state
# (checked/selected/value) carries meaning even without a name.
_TEXTUAL_INPUT_ROLES: frozenset[str] = frozenset({"textbox", "searchbox", "combobox", "spinbutton"})

# Truly transparent roles — anonymous DOM wrappers with no semantic meaning,
# emit children inline with no boundary.
#
# - ``listbox``: container for ``option`` items, no UI of its own; agents
#   target the options, not the listbox.
# - ``presentation``/``none``: WAI-ARIA roles meaning "treat as if absent."
#   Without these, sites that wrap atoms in such a role (Google Flights wraps
#   the trailing label + Destination button this way) inline-flow them into
#   one crammed atom via the unknown-role fallback.
_TRANSPARENT_ROLES: frozenset[str] = frozenset(
    {
        "generic",
        "group",
        "tooltip",
        "status",
        "alert",
        "progressbar",
        "listbox",
        "presentation",
        "none",
        "document",
        "application",
        "feed",
        "tree",
        "directory",
        "figure",
        "note",
        "log",
        "marquee",
        "timer",
    }
)

# Landmark roles — semantic page regions. Their content is still inline,
# but the region itself produces a paragraph boundary so distinct landmarks
# (page header, navigation, main, sidebar, footer, …) don't crash together
# into one inline run.
#
# "Strong" landmarks (HTML5 landmark elements + interactive containers) are
# treated as paragraph-bound unconditionally — they're virtually always real
# page sections.
#
# "Named" landmarks (``region``/``section``/``article``) only qualify when
# they carry an accessible name. Unnamed instances are often accidental —
# enterprise UIs sprinkle ``<section>`` liberally — so we leave them
# transparent to avoid over-separating small widgets.
_STRONG_LANDMARK_ROLES: frozenset[str] = frozenset(
    {
        "banner",
        "navigation",
        "main",
        "complementary",
        "contentinfo",
        "dialog",
        "alertdialog",
        "tabpanel",
    }
)
_NAMED_LANDMARK_ROLES: frozenset[str] = frozenset({"region", "section", "article"})
_LANDMARK_ROLES: frozenset[str] = _STRONG_LANDMARK_ROLES | _NAMED_LANDMARK_ROLES

# Grouping roles — logical groups of controls/items (a search form, a tab
# strip, a menu). We always fan their meaningful children out as paragraphs
# rather than letting them collapse onto an inline run.
_GROUPING_ROLES: frozenset[str] = frozenset({"form", "search", "tablist", "menubar", "menu", "radiogroup", "toolbar"})

# Layout-table parts handled as a family when they appear standalone (outside
# an actual data table that already structured them as a GitHub-Flavored Markdown pipe table).
_LAYOUT_PART_ROLES: frozenset[str] = frozenset({"row", "rowgroup", "cell", "gridcell", "columnheader", "rowheader"})

# Block-level rendered roles — they must never combine into a plain-text run
# with surrounding inline text, even when their rendered output happens to be
# single-line and carries no ``[ref=…]``.
_BLOCK_ATOM_ROLES: frozenset[str] = frozenset(
    {
        "heading",
        "paragraph",
        "list",
        "listitem",
        "table",
        "grid",
        "code",
        "separator",
        "blockquote",
        "figure",
    }
)

# A node header within the aria-snapshot YAML, e.g.
# ``combobox "menu" [expanded] [ref=e7]``. Captures the role, optional quoted
# name, and the trailing bracketed attributes blob (``[ref=…]``, ``[checked]``,
# ``[cursor=pointer]`` …) which we mine for the ref and state flags below.
_HEADER_PATTERN = re.compile(r'^(?P<role>[\w-]+)(?:\s+"(?P<name>.*?)")?(?P<attrs>(?:\s*\[[^\]]*\])*)\s*$')

# State flags Playwright emits as ``[flag]`` or ``[flag=value]`` — the
# element's interactable state. We surface these; ``[ref=…]`` / ``[active]`` /
# ``[level=…]`` / ``[cursor=…]`` are excluded (handled elsewhere or low value).
_STATE_FLAG_PATTERN = re.compile(
    r"\[(?P<flag>checked|disabled|selected|expanded|pressed|readonly)"
    r"(?:=(?P<val>[\w-]+))?\]"
)

# Heading depth: aria emits ``[level=N]`` for ``<h1>``…``<h6>``.
_LEVEL_PATTERN = re.compile(r"\[level=(\d+)\]")

# Any ``[ref=eN]`` token, in either markdown body or raw YAML.
_REF_PATTERN = re.compile(r"\[ref=(e\d+)\]")


# ── Tree primitives ─────────────────────────────────────────────────────
# aria_snapshot(mode="ai") parses to nested str/dict structures. PyYAML owns
# the hierarchy/nesting/escaping; we only parse each node's header string.


def _split_node(node: Any) -> tuple[str | None, Any]:
    """Return ``(header, body)`` for a YAML aria node (str leaf or 1-key dict)."""
    if isinstance(node, str):
        return node, None
    if isinstance(node, dict) and len(node) == 1:
        ((header, body),) = node.items()
        return header, body
    return None, None


def _parse_header(header: str) -> tuple[str, str, str | None, tuple[str, ...], bool] | None:
    """Parse ``role "name" [attr]…`` into (role, name, ref, state, clickable).

    ``clickable`` reflects Playwright's ``[cursor=pointer]`` hint — used to
    recover non-semantic but clickable ``generic`` elements.
    """
    m = _HEADER_PATTERN.match(header.strip())
    if m is None:
        return None
    attrs = m.group("attrs") or ""
    ref_m = _REF_PATTERN.search(attrs)
    state = tuple(
        f.group("flag") + (f"={f.group('val')}" if f.group("val") else "") for f in _STATE_FLAG_PATTERN.finditer(attrs)
    )
    clickable = "[cursor=pointer]" in attrs
    return (
        m.group("role"),
        m.group("name") or "",
        (ref_m.group(1) if ref_m else None),
        state,
        clickable,
    )


def _find_url_child(children: list[Any]) -> str | None:
    for c in children:
        h, b = _split_node(c)
        if h is not None and h.strip().startswith("/url") and b is not None:
            return str(b).strip()
    return None


def _is_url_node(node: Any) -> bool:
    h, _ = _split_node(node)
    return h is not None and h.strip().startswith("/url")


# ── Descendant scans ─────────────────────────────────────────────────────


def _native_select_options(children: list[Any]) -> list[str]:
    """Labels of ref-less ``option`` descendants — the tell for a native <select>.

    A native ``<select>`` nests its ``<option>``s (without refs) even when
    collapsed; a collapsed ARIA combobox has no children and an expanded one's
    options sit in a sibling listbox with refs.
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
                if (role in _INTERACTIVE_ROLES and ref is not None) or (role == "generic" and clickable):
                    return True
        if isinstance(body, list) and _has_click_target(body):
            return True
    return False


def _count_click_targets(nodes: list[Any], limit: int = 2) -> int:
    """Count interactable / clickable-generic descendants, capped at ``limit``.

    Distinguishes a *thin* hit-area wrapper (≤1 target — a ``cursor=pointer``
    div around a single button, just a bigger tap zone) from a *card* (≥2 — a
    result row / product tile whose own click is a distinct action from any
    button it contains). Short-circuits once ``limit`` is reached.
    """
    n = 0
    for node in nodes:
        header, body = _split_node(node)
        if header is not None:
            parsed = _parse_header(header)
            if parsed is not None:
                role, _, ref, _, clickable = parsed
                if (role in _INTERACTIVE_ROLES and ref is not None) or (role == "generic" and clickable):
                    n += 1
        if n < limit and isinstance(body, list):
            n += _count_click_targets(body, limit - n)
        if n >= limit:
            return limit
    return n


# Min sibling record-generics to treat a run as a record list (see ``_fragments``).
_RECORD_RUN_MIN = 3


def _is_record_generic(node: Any) -> bool:
    """True if ``node`` is a non-clickable ``generic``/``group`` wrapping ≥2
    interactive descendants — a de-facto record (a search-result / paper row).

    Used to detect a *run* of such siblings: when ≥2 sit together they are a
    record list, and each must render as its own block so they don't collapse
    onto one inline line (the ``generic``-equivalent of the clickable CARD rule).
    """
    header, body = _split_node(node)
    if header is None or header.strip().startswith("/url"):
        return False
    parsed = _parse_header(header)
    if parsed is None:
        return False
    role, _, _, _, clickable = parsed
    if role not in ("generic", "group") or clickable:
        return False
    kids = body if isinstance(body, list) else []
    return _count_click_targets(kids) >= 2


def _collect_interactive_refs(children: list[Any]) -> list[str]:
    """Interactive descendant refs in document order — anchors orphans.

    When a parent (button/link/form-control) renders by its name and skips
    recursing into its children, any *interactive* descendant refs would be
    lost. We sweep them up and append next to the parent's ref so the agent
    can still target them.
    """
    out: list[str] = []
    for c in children:
        h, b = _split_node(c)
        if h is None or h.strip().startswith("/url"):
            continue
        parsed = _parse_header(h)
        if parsed is not None:
            role, _, ref, _, _ = parsed
            if ref and role in _INTERACTIVE_ROLES:
                out.append(ref)
        if isinstance(b, list):
            out.extend(_collect_interactive_refs(b))
    return out


def _swept_refs(children: list[Any]) -> str:
    """Tag string for descendant interactive refs (empty if none)."""
    return "".join(f" [ref={r}]" for r in _collect_interactive_refs(children))


# ── Render context ───────────────────────────────────────────────────────


@dataclass
class _Ctx:
    """Per-node context passed to role handlers.

    ``flow=True`` means we're inside a prose flow (paragraph, heading, link,
    listitem text, cell): inline atoms concatenate. ``flow=False`` (top level
    or inside a structural container) means transparent multi-child containers
    fan out as nested bullets — the rule that tames the SPA-divs-deep wall.
    """

    role: str
    name: str
    ref: str | None
    state: tuple[str, ...]
    clickable: bool
    children: list[Any]
    value: str | None
    ref_tag: str
    header: str
    depth: int
    flow: bool


# ── Per-role renderers ───────────────────────────────────────────────────
# Each handler takes a ``_Ctx`` and returns a markdown fragment. The dispatch
# table at the bottom of the file maps role strings to these handlers.


def _render_heading(ctx: _Ctx) -> str:
    m = _LEVEL_PATTERN.search(ctx.header)
    level = max(1, min(int(m.group(1)) if m else 2, 6))
    # Prefer rendered children: preserves any inner link/button refs that
    # accessible-name flattening would otherwise drop. Fall back to name, then
    # to a scalar body (``heading: "text"``) so a plain-text heading isn't lost.
    content = _kids_md(ctx.children, ctx.depth, flow=True).strip() or ctx.name or (ctx.value or "")
    return f"\n\n{'#' * level} {content}\n\n"


def _render_paragraph(ctx: _Ctx) -> str:
    # A plain-text paragraph arrives as a scalar body (``paragraph: "..."``),
    # landing in ``ctx.value`` with no children — fall back to it (then name)
    # so prose paragraphs aren't dropped. Mirrors ``_render_heading``/``_render_code``.
    content = _kids_md(ctx.children, ctx.depth, flow=True).strip() or ctx.value or ctx.name
    if not content:
        return ""
    return f"\n\n{content}\n\n"


def _render_code(ctx: _Ctx) -> str:
    body = ctx.name or ctx.value or _kids_md(ctx.children, ctx.depth, flow=True).strip()
    # Multi-line content (aria sometimes condenses with " ... ") → fence.
    if "\n" in body or len(body) > 80:
        return f"\n\n```\n{body}\n```\n\n"
    return f"`{body}`"


def _render_separator(ctx: _Ctx) -> str:
    return "\n\n---\n\n"


# Inline text-formatting roles → standard markdown delimiters. Flow-safe: they
# only wrap the rendered text, so they concatenate into prose runs and group into
# list bullets exactly like the plain text they replace — but stay regex-separable
# (e.g. ``**title** *authors*`` in a paper-listing ``listitem``). Only roles with a
# portable CommonMark/GFM representation belong here; ``insertion``/``subscript``/
# ``superscript``/``mark``/``time``/``math`` have none, so they stay plain-text
# passthrough via ``_render_unknown`` rather than gaining non-standard syntax.
_INLINE_MARKUP: dict[str, tuple[str, str]] = {
    "strong": ("**", "**"),
    "emphasis": ("*", "*"),
    "deletion": ("~~", "~~"),  # GFM strikethrough
    "term": ("**", "**"),  # <dt> label in a <dl> definition list
}


def _render_inline_markup(ctx: _Ctx) -> str:
    pre, post = _INLINE_MARKUP[ctx.role]
    body = ctx.value or _kids_md(ctx.children, ctx.depth, flow=True).strip()
    return f"{pre}{body}{post}" if body else ""


# Interactive roles with no dedicated widget rendering that still must surface as
# a clickable atom (``role "name" [state] [ref=eN]``). Without a handler they fall
# to ``_render_unknown`` and vanish entirely — ref and all — so the agent loses the
# element (the original ``menuitem`` / ``treeitem`` bug). ``menuitem*`` carry
# checked/selected state; ``scrollbar`` is a range widget.
_INTERACTIVE_ATOM_ROLES: frozenset[str] = frozenset(
    {"menuitem", "menuitemcheckbox", "menuitemradio", "treeitem", "scrollbar"}
)


def _render_interactive_atom(ctx: _Ctx) -> str:
    body = ctx.name or _inline_name(ctx.children, ctx.depth)
    state = "".join(f" [{f}]" for f in ctx.state)
    extra = _swept_refs(ctx.children) if ctx.name else ""
    head = f'{ctx.role} "{body}"' if body else ctx.role
    return f"{head}{state}{ctx.ref_tag}{extra}"


def _render_blockquote(ctx: _Ctx) -> str:
    inner = _kids_md(ctx.children, ctx.depth, flow=True).strip() or ctx.value or ctx.name
    if not inner:
        return ""
    quoted = "\n".join(f"> {ln}" if ln else ">" for ln in inner.splitlines())
    return f"\n\n{quoted}\n\n"


# Roles with no portable CommonMark/GFM representation — emit their text and let
# it flow with neighbors (a ``deletion`` pairs with ``term`` bold, a ``caption``
# trails its figure). Inventing non-standard syntax (``==mark==``, ``<sub>``) would
# add noise and break naive regex, so these stay plain. Registered explicitly,
# rather than left to the ``_render_unknown`` fallback, so the ARIA role set is
# covered exhaustively and the coverage is testable.
_PLAIN_TEXT_ROLES: frozenset[str] = frozenset(
    {"insertion", "subscript", "superscript", "math", "time", "meter", "caption", "definition"}
)


def _render_plain_text(ctx: _Ctx) -> str:
    leading = (ctx.value + " ") if ctx.value else ""
    return leading + _kids_md(ctx.children, ctx.depth, flow=ctx.flow)


def _render_text(ctx: _Ctx) -> str:
    return ctx.value or ""


# Leading block decoration a flattened accessible name must shed (heading ``## ``,
# blockquote ``> ``, bullet ``- ``, fence/horizontal-rule line) so an interactive
# atom that wraps block content stays a clean single-line ``[text] [ref=eN]``.
_BLOCK_DECORATION_RE = re.compile(r"^\s*(?:#{1,6}\s+|>\s?|[-*+]\s+|```.*$|-{3,}\s*$)")


def _inline_name(children: list[Any], depth: int) -> str:
    """Flatten an interactive element's children into a one-line accessible name.

    Block markup (heading/blockquote/fence/rule prefixes) and newlines are
    stripped so an atom wrapping block content — the ubiquitous
    ``<a href><h3>Title</h3><p>desc</p></a>`` card — renders as a single-line
    ``[Title desc](url) [ref=eN]`` atom rather than splintering across lines and
    breaking the per-line ref contract the snapshot relies on.
    """
    out: list[str] = []
    for ln in _kids_md(children, depth, flow=True).splitlines():
        ln = _BLOCK_DECORATION_RE.sub("", ln).strip()
        if ln:
            out.append(ln)
    return " ".join(out)


def _render_link(ctx: _Ctx) -> str:
    href = _find_url_child(ctx.children)
    # Drop aria-only ``<a>`` elements: no href and no ref means the link exists
    # solely as a screen-reader description, with no navigation target or
    # interactable handle. Be visible-content-centric.
    if not href and not ctx.ref:
        return ""
    kids = [c for c in ctx.children if not _is_url_node(c)]
    body = ctx.name or _inline_name(kids, ctx.depth)
    # When we used ``name`` (and so skipped recursing into kids), sweep up any
    # interactive descendant refs so they aren't orphaned.
    extra = _swept_refs(kids) if ctx.name else ""
    if href:
        return f"[{body}]({href}){ctx.ref_tag}{extra}"
    return f"[{body}]{ctx.ref_tag}{extra}"


def _render_button(ctx: _Ctx) -> str:
    body = ctx.name or _inline_name(ctx.children, ctx.depth)
    extra = _swept_refs(ctx.children) if ctx.name else ""
    if body:
        return f'button "{body}"{ctx.ref_tag}{extra}'
    return f"button{ctx.ref_tag}{extra}"


def _render_img(ctx: _Ctx) -> str:
    # Drop nameless images: ``![]()`` carries no information and is the main
    # source of icon-noise on JS-heavy UIs.
    if not ctx.name:
        return ""
    return f"![{ctx.name}](){ctx.ref_tag}"


def _render_option(ctx: _Ctx) -> str:
    # A ref'd ``option`` (live listbox / autocomplete suggestion) — surface it
    # so the agent can click it. Ref-less options inside native ``<select>``
    # are handled separately via ``_native_select_options``.
    if ctx.ref is None:
        return ""
    return f'option "{ctx.name}"{ctx.ref_tag}' if ctx.name else f"option{ctx.ref_tag}"


def _render_list(ctx: _Ctx) -> str:
    # Strip only newlines, not spaces: a sub-list nested under a listitem renders
    # its items pre-indented, and stripping leading spaces would de-indent the
    # first item relative to its siblings.
    inner = _emit_block_frags(_fragments(ctx.children, ctx.depth, flow=False), ctx.depth).strip("\n")
    return f"\n\n{inner}\n\n" if inner else ""


def _render_listitem(ctx: _Ctx) -> str:
    """Render a listitem: the first inline run leads the bullet line, remaining
    units nest at ``depth+1``. Transparent descendants are flattened by
    ``_fragments`` so SPA rows (flights, search results) stay one level deep;
    nested ``list``/``table`` children keep their structure as standalone
    blocks. A clickable card leads the row with its ref hoisted onto the line.
    """
    indent = "  " * ctx.depth
    frags = ([_Frag(TEXT, ctx.value)] if ctx.value else []) + _fragments(ctx.children, ctx.depth + 1, flow=False)
    units = _merge_runs(frags)
    if not units:
        return f"\n{indent}-{ctx.ref_tag}" if ctx.ref_tag.strip() else ""
    first, rest = units[0], units[1:]
    if first.kind == CARD:
        lines = _card_bullets(first, ctx.depth)
    else:
        lines = _unit_bullets(first, ctx.depth)
        # The listitem's own ref attaches only when it has a single inline leaf.
        if len(units) == 1 and ctx.ref_tag.strip() and first.kind in (TEXT, ATOM):
            lines[0] += ctx.ref_tag
    for u in rest:
        lines.extend(_unit_bullets(u, ctx.depth + 1))
    return "\n" + "\n".join(lines) + "\n"


def _render_table_node(ctx: _Ctx) -> str:
    """A ``table``/``grid``. Real data tables become GitHub-Flavored Markdown pipe tables; layout
    tables (Hacker News's outer chrome) fall back to bullet rendering."""
    if _is_data_table(ctx.children):
        return f"\n\n{_render_md_table(ctx.children)}\n\n"
    return _emit_block_frags(_fragments(ctx.children, ctx.depth, flow=False), ctx.depth)


def _render_form_control(ctx: _Ctx) -> str:
    """Render a form control inline as ``role "name" = "value" [flag] [ref=eN]``.

    For native ``<select>`` comboboxes, also folds option labels inline (capped
    at ``_MAX_NATIVE_OPTIONS``) so the agent knows what values ``browser_select``
    accepts.

    A form control whose children include interactive descendants (an expanded
    combobox with nested options, an autocomplete textbox with a child listbox,
    a custom widget exposing inner buttons) renders as a header line followed
    by those children as a sub-list.

    Bare textual inputs (textbox/searchbox/combobox/spinbutton with no name,
    no value, and no interactive descendants) are dropped — see
    ``_TEXTUAL_INPUT_ROLES`` for the rationale.
    """
    has_interactive_kids = _has_click_target(ctx.children)
    derived_value: str | None = None
    if ctx.value is None and ctx.children and not has_interactive_kids:
        # Children are accessible-name composition (icon + text), not options.
        kids = _inline_name(ctx.children, depth=0)
        if kids:
            derived_value = kids

    if (
        ctx.role in _TEXTUAL_INPUT_ROLES
        and not ctx.name
        and ctx.value is None
        and derived_value is None
        and not has_interactive_kids
    ):
        return ""

    parts: list[str] = [ctx.role]
    if ctx.name:
        parts.append(f'"{ctx.name}"')
    if ctx.value is not None:
        parts.append(f'= "{ctx.value}"')
    elif derived_value is not None:
        parts.append(f'= "{derived_value}"')
    for flag in ctx.state:
        parts.append(f"[{flag}]")
    if ctx.role == "combobox" and not has_interactive_kids:
        # Native <select>: ref-less options live as direct children.
        options = _native_select_options(ctx.children)
        if options:
            opts = ", ".join(f'"{o}"' for o in options[:_MAX_NATIVE_OPTIONS])
            more = " …" if len(options) > _MAX_NATIVE_OPTIONS else ""
            parts.append(f"— options: {opts}{more}")
    if ctx.ref_tag:
        parts.append(ctx.ref_tag.strip())
    rendered = " ".join(parts)

    if has_interactive_kids:
        # An active widget (expanded combobox, autocomplete) — its header line
        # is followed by the interactive children as a sub-list. Flattening and
        # grouping are the shared IR path, same as ``_render_listitem``.
        sub_indent = "  " * (ctx.depth + 1)
        bullets: list[str] = []
        for u in _merge_runs(_fragments(ctx.children, ctx.depth + 1, flow=False)):
            bullets.extend(_unit_bullets(u, ctx.depth + 1) if u.kind != TEXT else [f"{sub_indent}- {u.text}"])
        if bullets:
            rendered += "\n" + "\n".join(bullets)
        return rendered

    # Sweep interactive descendant refs (rare: e.g. a button inside a label).
    if ctx.name:
        rendered += _swept_refs(ctx.children)
    return rendered


def _render_grouping(ctx: _Ctx) -> str:
    """Form / search / tablist / menu containers.

    Flatten transparent descendants, then emit each unit as its own paragraph.
    Avoids indent inversion from arbitrary DOM-wrapper depth (Google Flights'
    nested form generics, Wikipedia's search wrapper). A lone unit inlines;
    consecutive plain-text merges into one paragraph (via ``_merge_runs``) while
    atoms keep their own.
    """
    units = _merge_runs(_fragments(ctx.children, ctx.depth, flow=False))
    if not units:
        return ""
    if len(units) == 1:
        leading = (ctx.value + " ") if ctx.value else ""
        return leading + _frag_inline(units[0])
    return "\n\n" + "\n\n".join(_frag_inline(u) for u in units) + "\n\n"


def _render_landmark(ctx: _Ctx) -> str:
    """Landmark roles (``banner``/``navigation``/``main``/…): emit children
    inline like a transparent container, but wrap with paragraph boundaries
    so adjacent landmarks render as distinct blocks rather than one big run.
    """
    inner = _kids_md(ctx.children, ctx.depth, flow=True).strip()
    return f"\n\n{inner}\n\n" if inner else ""


# ── Fragment IR ──────────────────────────────────────────────────────────
# The renderer runs in two phases. Phase 1 (``_fragments``) turns an aria
# child-list into a flat list of typed fragments — eliding transparent
# wrappers, resolving clickable cards, and classifying each surviving piece as
# inline-text / atom / block *by structure* (role + ref presence + shape), not
# by grepping rendered strings. Phase 2 (the ``_emit_*`` serializers) lays the
# fragments out per container: a flowing run, nested bullets, or paragraphs.
#
# This split is the single home for the two questions that used to be smeared
# across a threaded ``flow`` flag, ``(text, is_plain)`` tuples, and a
# ``"[ref=" in cm`` string match:
#   * inline vs block  — a fragment's ``kind``;
#   * mergeable text vs standalone atom — ``TEXT`` vs ``ATOM``.

# Fragment kinds:
#   TEXT  — plain inline text; consecutive TEXT fragments merge into one run.
#   ATOM  — a self-contained inline element (link/button/control/img/option/
#           clickable leaf, or a value-bearing generic carrying its ref anchor).
#           Inline in flow context; its own bullet in block context.
#   BLOCK — standalone block markdown (heading/paragraph/list/table/blockquote/
#           separator/fenced code, or any multi-line render). Never merges.
#   CARD  — a clickable container wrapping ≥2 distinct actions (a result row /
#           tile). Its own click is a real affordance; layout is deferred to the
#           container so the row handle can land on the row line, not dangle.
TEXT, ATOM, BLOCK, CARD = "text", "atom", "block", "card"


@dataclass
class _Frag:
    kind: str
    text: str = ""
    ref: str | None = None  # CARD: the row-level click handle
    name: str = ""  # CARD: accessible name, if any
    fields: list["_Frag"] = field(default_factory=list)  # CARD: inner row content


# Punctuation/closers that should hug the preceding token (no inserted space).
_NO_SPACE_BEFORE = frozenset(".,;:!?)]}>")


def _join_inline(parts: list[str]) -> str:
    """Concatenate inline strings, inserting a space at boundaries where both
    sides are non-whitespace and the next side isn't a closing punctuation.

    Prose pages have text nodes carrying their own whitespace ("is a ", " for
    managing data"); navigation menus and grouping containers don't (the visual
    spacing is CSS-only). Without this glue, adjacent buttons/links/boxes in a
    nav strip collide into one run like ``[X][Y]button "Z"``. Punctuation
    (``.``, ``,``, ``)`` …) must still hug the previous token, so we skip the
    space when the next fragment starts with a closer.
    """
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        if out and out[-1] and out[-1][-1] not in " \t\n" and p[0] not in " \t\n" and p[0] not in _NO_SPACE_BEFORE:
            out.append(" ")
        out.append(p)
    return "".join(out)


# Hard cap on render recursion. Every descent passes through ``_fragments`` (a
# transparent wrapper recurses it directly; a rendered node reaches it via its
# handler → ``_kids_md``), so guarding here bounds the whole walk. Set well below
# Python's recursion limit (~1000 frames; a level costs several) yet far above any
# real page's nesting, so pathological div-soup degrades (deep subtree dropped)
# instead of raising an uncaught ``RecursionError`` that fails the whole snapshot.
# Context-local so concurrent snapshot renders don't share the counter.
_MAX_RENDER_DEPTH = 120
_render_depth: contextvars.ContextVar[int] = contextvars.ContextVar("_aria_render_depth", default=0)


def _fragments(nodes: list[Any], depth: int, flow: bool) -> list[_Frag]:
    """Depth-guarded entry to :func:`_fragments_impl` (see there for behavior)."""
    rec = _render_depth.get()
    if rec >= _MAX_RENDER_DEPTH:
        return []  # pathological nesting: drop the deep subtree rather than crash
    token = _render_depth.set(rec + 1)
    try:
        return _fragments_impl(nodes, depth, flow)
    finally:
        _render_depth.reset(token)


def _fragments_impl(nodes: list[Any], depth: int, flow: bool) -> list[_Frag]:
    """Phase 1: aria child-list → flat typed fragments.

    Transparent wrappers (``generic``/``group``/landmark-less divs, standalone
    layout ``row``/``cell``) are elided — their children splice in here, the one
    place that decision lives. A clickable ``generic`` resolves by how many
    interactive descendants it wraps: 0 → a clickable leaf atom; exactly 1 → a
    redundant hit-area wrapper, demoted (ref dropped, children spliced); ≥2 → a
    ``CARD``. Everything else is rendered via its handler and classified.

    ``flow`` selects record vs label context. In block/record context
    (``flow=False``) a value-bearing generic keeps its ``[ref=…]`` inline as a
    field anchor, so a div-built row splits on refs like the raw aria tree. In
    label context (``flow=True`` — deriving a button/heading accessible name)
    the ref is omitted so labels stay clean.
    """
    # A run of ≥``_RECORD_RUN_MIN`` sibling record-generics is a record list
    # (search results, a paper index): each must render as its own block, else
    # they collapse onto one inline line. The threshold is >2 so a mere pair —
    # usually the two halves of a single record (an action bar + a title block) —
    # keeps flowing inline. (The top-level body renders at flow=True, so we can't
    # gate on flow; a leaf record is itself flowed inline, so accessible-name
    # derivation over such children stays single line.)
    record_run = sum(_is_record_generic(c) for c in nodes) >= _RECORD_RUN_MIN

    out: list[_Frag] = []
    for c in nodes:
        h, b = _split_node(c)
        if h is None or h.strip().startswith("/url"):
            continue
        parsed = _parse_header(h)
        if parsed is None:
            continue
        role, name, ref, _, clickable = parsed
        kids = b if isinstance(b, list) else []
        value = b if isinstance(b, str) else None

        if role in _TRANSPARENT_ROLES or role in _LAYOUT_PART_ROLES:
            if role == "generic" and clickable and ref is not None:
                targets = _count_click_targets(kids)
                if targets == 0:  # innermost clickable → atom
                    inner = _join_inline([value or "", _inline_name(kids, depth)]).strip()
                    out.append(_Frag(ATOM, f'clickable "{inner}" [ref={ref}]' if inner else f"clickable [ref={ref}]"))
                    continue
                if targets >= 2:  # card: its own click is a distinct affordance
                    out.append(_Frag(CARD, ref=ref, name=name, fields=_fragments(kids, depth, flow)))
                    continue
                # targets == 1: thin wrapper → elide (drop ref, splice children)
            if record_run and role in ("generic", "group") and not clickable and _count_click_targets(kids) >= 2:
                # A record in a record list, rendered as a standalone block so
                # siblings don't merge onto one line. A *leaf* record (no nested
                # records) flows inline as a single line; a *container* record
                # (one holding its own record list) fans its children out.
                sub = _fragments(kids, depth, flow=False)
                if any(f.kind in (BLOCK, CARD) for f in sub):
                    body_md = _emit_block_frags(sub, depth)
                else:
                    body_md = _emit_flow(_merge_runs(sub))
                if value:
                    body_md = _join_inline([value, body_md]) if "\n" not in body_md else value + "\n" + body_md
                if body_md.strip():
                    out.append(_Frag(BLOCK, body_md))
                continue
            if value:
                # A ref means "actionable". An informational ``generic`` (a
                # labelled <div>/<span> — a flight time, an airline name) is not
                # clickable, so it drops its ref to keep the row clean and keep
                # ``[ref=…]`` meaning "you can act here". Other transparent roles
                # (status/alert/listbox) keep theirs in block context. Clickable
                # generics never reach here — handled above as atoms/cards.
                keep_ref = ref and role != "generic" and not flow
                out.append(_Frag(TEXT, f"{value} [ref={ref}]" if keep_ref else value))
            if kids:
                out.extend(_fragments(kids, depth, flow))
            continue

        # Non-elided node: render via its handler, classify structurally.
        cm = _render_md_node(c, depth, flow=flow)
        if not cm.strip():
            continue
        # Block: a render with any newline — internal (a list/table) or just the
        # ``\n\n`` boundary a landmark/grouping wraps itself in — is a standalone
        # block region. Keep its boundaries intact so it stays separated when a
        # landmark flows its children inline, and is re-indented by the bullet
        # emitters. (A single-line inline atom/text never carries a newline.)
        if role in _BLOCK_ATOM_ROLES or "\n" in cm:
            out.append(_Frag(BLOCK, cm))
            continue
        s = cm.strip()
        if role in _INLINE_MARKUP or role in _PLAIN_TEXT_ROLES or role == "text":
            out.append(_Frag(TEXT, s))
        elif ref is not None or _collect_interactive_refs(kids):
            out.append(_Frag(ATOM, s))
        else:
            out.append(_Frag(TEXT, s))
    return out


def _merge_runs(frags: list[_Frag]) -> list[_Frag]:
    """Collapse consecutive ``TEXT`` fragments into one inline run; atoms,
    blocks and cards keep their own slot. The single grouping primitive shared
    by every container layout (replaces the thrice-duplicated buf/leaves loop).
    """
    out: list[_Frag] = []
    buf: list[str] = []
    for f in frags:
        if f.kind == TEXT:
            buf.append(f.text)
        else:
            if buf:
                out.append(_Frag(TEXT, _join_inline(buf)))
                buf = []
            out.append(f)
    if buf:
        out.append(_Frag(TEXT, _join_inline(buf)))
    return out


def _frag_inline(f: _Frag) -> str:
    """A fragment's inline string form (flow context)."""
    if f.kind == CARD:
        inner = _emit_flow(f.fields).strip() or f.name
        return f'clickable "{inner}" [ref={f.ref}]' if inner else f"clickable [ref={f.ref}]"
    return f.text


def _emit_flow(frags: list[_Frag]) -> str:
    """Phase 2 (flow): concatenate fragments inline with spacing glue.

    A ``BLOCK`` fragment never merges (a record-list row, a stray heading): it
    stands on its own line even here, so a record list under an inline-flow
    container doesn't collapse back onto one line.
    """
    parts = [_frag_inline(f) for f in frags]
    parts = ["\n" + p.strip("\n") + "\n" if f.kind == BLOCK and p.strip() else p for f, p in zip(frags, parts)]
    return _join_inline(parts)


def _unit_bullets(u: _Frag, depth: int) -> list[str]:
    """Render one merged unit as bullet line(s) at ``depth``."""
    indent = "  " * depth
    if u.kind == CARD:
        return _card_bullets(u, depth)
    if u.kind == BLOCK:
        cm = u.text.strip("\n")
        first_nb = cm.lstrip().split("\n", 1)[0].lstrip()
        if first_nb.startswith("- "):
            return [cm]  # already bullet lines — keep as-is
        if first_nb.startswith(("|", "#", "```")):
            return ["\n" + cm + "\n"]  # standalone block (table/heading/fence)
        first, _, rest = cm.partition("\n")
        return [f"{indent}- {first}"] + ([rest] if rest else [])
    first, _, rest = u.text.partition("\n")
    return [f"{indent}- {first}"] + ([rest] if rest else [])


def _card_bullets(card: _Frag, depth: int) -> list[str]:
    """Lay a ``CARD`` out as bullets: the row summary leads with the card's ref
    hoisted onto that line; inner action atoms follow as nested bullets. The
    card *is* the row, so its handle belongs on the row line, not dangling as a
    pseudo-child of its own content.
    """
    indent = "  " * depth
    units = _merge_runs(card.fields)
    lead: str | None = None
    sub: list[str] = []
    for u in units:
        if lead is None and u.kind == TEXT:
            lead = f"{indent}- {u.text} [ref={card.ref}]"
        else:
            sub.extend(_unit_bullets(u, depth + 1))
    if lead is None:  # no text fields — the card itself is the handle
        nm = f' "{card.name}"' if card.name else ""
        lead = f"{indent}- clickable{nm} [ref={card.ref}]"
    return [lead] + sub


def _emit_block_frags(frags: list[_Frag], depth: int) -> str:
    """Phase 2 (block): lay fragments out as nested bullets at ``depth``.

    A single inline child collapses to bare inline text (so ``generic > generic
    > link`` wrapper chains don't pile up bullets); otherwise each unit becomes
    its own bullet, with blocks kept standalone and cards hoisting their ref.
    """
    units = _merge_runs(frags)
    if not units:
        return ""
    if len(units) == 1:
        u = units[0]
        if u.kind in (TEXT, ATOM, BLOCK):
            return u.text
        return "\n" + "\n".join(_card_bullets(u, depth)) + "\n"
    lines: list[str] = []
    for u in units:
        lines.extend(_unit_bullets(u, depth))
    return "\n" + "\n".join(lines) + "\n"


def _kids_md(children: list[Any], depth: int, flow: bool = True) -> str:
    """Inline (label-context) render of a node's children — accessible-name
    derivation for headings/links/buttons/cells. Thin wrapper over the IR.
    """
    return _emit_flow(_fragments(children, depth, flow))


# ── Table helpers ────────────────────────────────────────────────────────


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


def _render_md_table(children: list[Any]) -> str:
    """Render a table's row children as a GitHub-Flavored Markdown pipe table."""
    rows = _flatten_rows(children)
    if not rows:
        return ""
    # Use a row as the header ONLY if it carries real ``columnheader``s. A layout/
    # listing table (Hacker News front page, job/flight/search result lists) has none;
    # promoting its first row would fabricate a header out of real data — which then
    # duplicates or drops that record if re-prepended to later chunks downstream. For
    # those, emit a blank header so every data row stays in the body, and the header
    # row reliably signals "no real header here".
    header_idx = next((i for i, r in enumerate(rows) if _row_has_role(r, "columnheader")), None)
    if header_idx is None:
        header_cells: list[str] = []
        body_rows = rows
    else:
        header_cells = _row_cells(rows[header_idx])
        body_rows = rows[:header_idx] + rows[header_idx + 1 :]
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
            # Sanitize pipe characters that would break the GitHub-Flavored Markdown table.
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


def _render_unknown(ctx: _Ctx) -> str:
    """Fallback for roles with no registered handler — inline-transparent.

    Children flow with surrounding text in flow context, fan out as bullets
    otherwise (same semantics as ``_render_transparent``). The single point
    to change if unknown roles should be handled differently.
    """
    leading = (ctx.value + " ") if ctx.value else ""
    return leading + _kids_md(ctx.children, ctx.depth, flow=ctx.flow)


# ── Dispatch table ──────────────────────────────────────────────────────
# Single source of truth: role → handler. Role families that share a handler
# (form controls, layout parts, grouping, transparent, strong landmarks) are
# expanded inline. Two cases stay as predicates in ``_render_md_node`` because
# they need state beyond the role:
#   - clickable-generic (``role=generic`` + clickable + leaf): promote to atom.
#   - named landmark (``region``/``section``/``article``): only when named.


_ROLE_HANDLERS: dict[str, Callable[[_Ctx], str]] = {
    # Block-level markdown forms.
    "heading": _render_heading,
    "paragraph": _render_paragraph,
    "code": _render_code,
    "separator": _render_separator,
    "blockquote": _render_blockquote,
    "list": _render_list,
    "listitem": _render_listitem,
    "table": _render_table_node,
    "grid": _render_table_node,
    "treegrid": _render_table_node,
    # Inline atoms.
    "text": _render_text,
    "link": _render_link,
    "button": _render_button,
    "img": _render_img,
    "option": _render_option,
    # Role families.
    **{r: _render_inline_markup for r in _INLINE_MARKUP},
    **{r: _render_interactive_atom for r in _INTERACTIVE_ATOM_ROLES},
    **{r: _render_plain_text for r in _PLAIN_TEXT_ROLES},
    **{r: _render_form_control for r in _FORM_CONTROL_ROLES},
    **{r: _render_grouping for r in _GROUPING_ROLES},
    **{r: _render_landmark for r in _STRONG_LANDMARK_ROLES},
}
# Transparent + layout-part roles have no handler: the walker routes them
# through ``_fragments`` (elision / card resolution) before dispatch.


# ── Walker ──────────────────────────────────────────────────────────────


def _render_md_node(node: Any, depth: int = 0, flow: bool = False) -> str:
    """Render one aria YAML node as a markdown fragment."""
    header, body = _split_node(node)
    if header is None or header.startswith("/url"):
        return ""
    parsed = _parse_header(header)
    if parsed is None:
        return ""
    role, name, ref, state, clickable = parsed
    children = body if isinstance(body, list) else []
    value = str(body) if isinstance(body, str | int | float) else None

    # Transparent wrappers, standalone layout parts, and clickable generics
    # (leaf / thin-wrapper / card) are resolved structurally by ``_fragments``,
    # then serialized inline (flow) or as bullets (block).
    if role in _TRANSPARENT_ROLES or role in _LAYOUT_PART_ROLES:
        frags = _fragments([node], depth, flow)
        return _emit_flow(frags) if flow else _emit_block_frags(frags, depth)

    ctx = _Ctx(
        role=role,
        name=name,
        ref=ref,
        state=state,
        clickable=clickable,
        children=children,
        value=value,
        ref_tag=f" [ref={ref}]" if ref else "",
        header=header,
        depth=depth,
        flow=flow,
    )

    # Named landmarks (region/section/article) only become blocks when named.
    if role in _NAMED_LANDMARK_ROLES and name:
        return _render_landmark(ctx)

    handler = _ROLE_HANDLERS.get(role, _render_unknown)
    return handler(ctx)


# ── Public API ──────────────────────────────────────────────────────────


def render_aria_markdown(aria_yaml: str) -> str:
    """Render an aria-snapshot YAML string as markdown with refs inlined."""
    try:
        tree = yaml.load(aria_yaml, Loader=_YamlLoader)
    except (yaml.YAMLError, RecursionError):  # RecursionError: pathologically deep YAML nesting
        return ""
    if not isinstance(tree, list):
        return ""
    # Top-level defaults to flow=True (prose-friendly): paragraphs and headings
    # emit their own markdown, and page-wrapping generics inline normally.
    # Listitems/grouping switch to flow=False for their children so multi-child
    # generics fan out as nested bullets instead of producing a wall.
    try:
        text = "".join(_render_md_node(n, depth=0, flow=True) for n in tree)
    except RecursionError:  # backstop below the _MAX_RENDER_DEPTH cap
        return ""
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def extract_refs(text: str) -> list[str]:
    """Return every ``[ref=eN]`` id present in ``text`` (markdown or YAML),
    deduplicated and in the order they first appear (i.e. document/traversal
    order), so callers can show refs to the agent in the order they are seen
    on the page.
    """
    return list(dict.fromkeys(_REF_PATTERN.findall(text)))
