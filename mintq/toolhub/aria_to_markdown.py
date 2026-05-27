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

rendered as markdown::

    - 11:59 PM - 12:32 PM +1 Frontier 9 hr 33 min SFO - EWR
      - button "Carbon emissions estimate..." [ref=e394]
      - button "Flight details..." [ref=e415]

About 2.7x to 4.8x smaller than raw aria across four real pages
(flights, wikipedia, Hacker News, tabulator).  Uses real markdown (GitHub Markdown tables,
nested bullets, prose flow) and drops aria-only narrations and
non-clickable informational refs so the snapshot matches what a sighted
user sees.

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
:class:`mintq.toolhub.message_store.MessageStore`), the same atom shape
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

import re
from dataclasses import dataclass
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
        "button", "link", "textbox", "combobox", "checkbox", "radio",
        "menuitem", "menuitemcheckbox", "menuitemradio", "tab", "switch",
        "slider", "spinbutton", "searchbox", "option",
    }
)

# Form-control roles render inline as ``role "name" = "value" [flag] [ref=eN]``.
_FORM_CONTROL_ROLES: frozenset[str] = frozenset(
    {
        "textbox", "searchbox", "combobox", "checkbox", "radio", "switch",
        "slider", "spinbutton", "tab",
    }
)

# Truly transparent roles — anonymous DOM wrappers with no semantic meaning,
# emit children inline with no boundary.
_TRANSPARENT_ROLES: frozenset[str] = frozenset(
    {"generic", "group", "tooltip", "status", "alert", "progressbar"}
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
        "banner", "navigation", "main", "complementary", "contentinfo",
        "dialog", "alertdialog", "tabpanel",
    }
)
_NAMED_LANDMARK_ROLES: frozenset[str] = frozenset(
    {"region", "section", "article"}
)
_LANDMARK_ROLES: frozenset[str] = _STRONG_LANDMARK_ROLES | _NAMED_LANDMARK_ROLES

# Grouping roles — logical groups of controls/items (a search form, a tab
# strip, a menu). We always fan their meaningful children out as paragraphs
# rather than letting them collapse onto an inline run.
_GROUPING_ROLES: frozenset[str] = frozenset(
    {"form", "search", "tablist", "menubar", "menu"}
)

# Layout-table parts handled as a family when they appear standalone (outside
# an actual data table that already structured them as a GitHub-Flavored Markdown pipe table).
_LAYOUT_PART_ROLES: frozenset[str] = frozenset(
    {"row", "rowgroup", "cell", "gridcell", "columnheader", "rowheader"}
)

# Block-level rendered roles — they must never combine into a plain-text run
# with surrounding inline text, even when their rendered output happens to be
# single-line and carries no ``[ref=…]``.
_BLOCK_ATOM_ROLES: frozenset[str] = frozenset(
    {
        "heading", "paragraph", "list", "listitem", "table", "grid", "code",
        "separator", "blockquote", "figure",
    }
)

# A node header within the aria-snapshot YAML, e.g.
# ``combobox "menu" [expanded] [ref=e7]``. Captures the role, optional quoted
# name, and the trailing bracketed attributes blob (``[ref=…]``, ``[checked]``,
# ``[cursor=pointer]`` …) which we mine for the ref and state flags below.
_HEADER_PATTERN = re.compile(
    r'^(?P<role>[\w-]+)(?:\s+"(?P<name>.*?)")?(?P<attrs>(?:\s*\[[^\]]*\])*)\s*$'
)

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
        (header, body), = node.items()
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
        f.group("flag") + (f"={f.group('val')}" if f.group("val") else "")
        for f in _STATE_FLAG_PATTERN.finditer(attrs)
    )
    clickable = "[cursor=pointer]" in attrs
    return (
        m.group("role"),
        m.group("name") or "",
        (ref_m.group(1) if ref_m else None),
        state,
        clickable,
    )


def _meaningful_children(children: list[Any]) -> list[Any]:
    """Drop empty/skippable nodes (``/url`` annotations) before bulleting."""
    out: list[Any] = []
    for c in children:
        h, _ = _split_node(c)
        if h is None or h.strip().startswith("/url"):
            continue
        out.append(c)
    return out


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
                if (role in _INTERACTIVE_ROLES and ref is not None) or (
                    role == "generic" and clickable
                ):
                    return True
        if isinstance(body, list) and _has_click_target(body):
            return True
    return False


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
    # accessible-name flattening would otherwise drop.
    content = _kids_md(ctx.children, ctx.depth, flow=True).strip() or ctx.name
    return f"\n\n{'#' * level} {content}\n\n"


def _render_paragraph(ctx: _Ctx) -> str:
    return f"\n\n{_kids_md(ctx.children, ctx.depth, flow=True).strip()}\n\n"


def _render_code(ctx: _Ctx) -> str:
    body = ctx.name or ctx.value or _kids_md(ctx.children, ctx.depth, flow=True).strip()
    # Multi-line content (aria sometimes condenses with " ... ") → fence.
    if "\n" in body or len(body) > 80:
        return f"\n\n```\n{body}\n```\n\n"
    return f"`{body}`"


def _render_separator(ctx: _Ctx) -> str:
    return "\n\n---\n\n"


def _render_text(ctx: _Ctx) -> str:
    return ctx.value or ""


def _render_link(ctx: _Ctx) -> str:
    href = _find_url_child(ctx.children)
    # Drop aria-only ``<a>`` elements: no href and no ref means the link exists
    # solely as a screen-reader description, with no navigation target or
    # interactable handle. Be visible-content-centric.
    if not href and not ctx.ref:
        return ""
    kids = [c for c in ctx.children if not _is_url_node(c)]
    body = ctx.name or _kids_md(kids, ctx.depth, flow=True).strip()
    # When we used ``name`` (and so skipped recursing into kids), sweep up any
    # interactive descendant refs so they aren't orphaned.
    extra = _swept_refs(kids) if ctx.name else ""
    if href:
        return f"[{body}]({href}){ctx.ref_tag}{extra}"
    return f"[{body}]{ctx.ref_tag}{extra}"


def _render_button(ctx: _Ctx) -> str:
    body = ctx.name or _kids_md(ctx.children, ctx.depth, flow=True).strip()
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
    return f"\n\n{_kids_md(ctx.children, ctx.depth, flow=False).strip()}\n\n"


def _render_listitem(ctx: _Ctx) -> str:
    """Render a listitem at ``depth``, with leaves at ``depth+1`` as bullets.

    Transparent-generic descendants are flattened into a single level of
    bullets — keeps SPA UIs (flight rows, search results) readable without
    arbitrarily-deep nesting. Nested ``list``/``table`` children stop the
    flattening so real sub-lists and tables keep their structure.
    """
    indent = "  " * ctx.depth
    sub_indent = "  " * (ctx.depth + 1)
    raw: list[tuple[str, bool]] = []
    if ctx.value:
        raw.append((ctx.value, True))
    _flatten_to_leaves(ctx.children, ctx.depth + 1, raw)
    # Group consecutive plain-text leaves into single bullets; actionable
    # atoms (buttons, links, form controls, clickable generics) stay separate.
    leaves: list[str] = []
    buf: list[str] = []
    for text, is_plain in raw:
        if is_plain:
            buf.append(text)
        else:
            if buf:
                leaves.append(" ".join(buf))
                buf = []
            leaves.append(text)
    if buf:
        leaves.append(" ".join(buf))
    if not leaves:
        return f"\n{indent}-{ctx.ref_tag}" if ctx.ref_tag.strip() else ""
    # First group on the bullet line; remainder as nested bullets at depth+1.
    head_first, _, head_rest = leaves[0].partition("\n")
    out = f"\n{indent}- {head_first}" + (ctx.ref_tag if len(leaves) == 1 else "")
    if head_rest:
        out += "\n" + head_rest
    for leaf in leaves[1:]:
        first, _, rest = leaf.partition("\n")
        out += f"\n{sub_indent}- {first}"
        if rest:
            out += "\n" + rest
    return out


def _render_table_node(ctx: _Ctx) -> str:
    """A ``table``/``grid``. Real data tables become GitHub-Flavored Markdown pipe tables; layout
    tables (Hacker News's outer chrome) fall back to bullet rendering."""
    if _is_data_table(ctx.children):
        return f"\n\n{_render_md_table(ctx.children)}\n\n"
    return _bullet_block(ctx.value, ctx.children, ctx.depth, ctx.ref_tag)


def _render_layout_part(ctx: _Ctx) -> str:
    """A standalone row/cell/rowgroup outside a data table (e.g., Hacker News layout)."""
    if ctx.flow:
        leading = (ctx.value + " ") if ctx.value else ""
        return leading + _kids_md(ctx.children, ctx.depth, flow=True)
    return _bullet_block(ctx.value, ctx.children, ctx.depth, ctx.ref_tag)


def _render_form_control(ctx: _Ctx) -> str:
    """Render a form control inline as ``role "name" = "value" [flag] [ref=eN]``.

    For native ``<select>`` comboboxes, also folds option labels inline (capped
    at ``_MAX_NATIVE_OPTIONS``) so the agent knows what values ``browser_select``
    accepts.

    An expanded ARIA combobox with nested interactive children (some sites
    inline their options instead of placing them in a sibling listbox)
    renders as a header line followed by the options as a sub-list — not
    crammed into the ``= "value"`` slot, where nested quotes plus a sweep
    of every descendant ref produced an unreadable blob.
    """
    expanded_with_options = (
        ctx.role == "combobox"
        and "expanded" in ctx.state
        and ctx.value is None
        and _has_click_target(ctx.children)
    )

    parts: list[str] = [ctx.role]
    if ctx.name:
        parts.append(f'"{ctx.name}"')
    if ctx.value is not None:
        parts.append(f'= "{ctx.value}"')
    elif ctx.children and not expanded_with_options:
        kids = _kids_md(ctx.children, depth=0, flow=True).strip()
        if kids:
            parts.append(f'= "{kids}"')
    for flag in ctx.state:
        parts.append(f"[{flag}]")
    if ctx.role == "combobox" and not expanded_with_options:
        options = _native_select_options(ctx.children)
        if options:
            opts = ", ".join(f'"{o}"' for o in options[:_MAX_NATIVE_OPTIONS])
            more = " …" if len(options) > _MAX_NATIVE_OPTIONS else ""
            parts.append(f"— options: {opts}{more}")
    if ctx.ref_tag:
        parts.append(ctx.ref_tag.strip())
    rendered = " ".join(parts)
    if expanded_with_options:
        indent = "  " * (ctx.depth + 1)
        bullets: list[str] = []
        for child in _meaningful_children(ctx.children):
            cm = _render_md_node(child, ctx.depth + 1, flow=False).strip("\n")
            if not cm.strip():
                continue
            first_nonblank = cm.lstrip()
            if first_nonblank.startswith("- "):
                bullets.append(cm)
            else:
                bullets.append(f"{indent}- {cm.strip()}")
        if bullets:
            rendered += "\n" + "\n".join(bullets)
        return rendered
    # Sweep interactive descendant refs (rare: e.g. a button inside a label).
    if ctx.name:
        rendered += _swept_refs(ctx.children)
    return rendered


def _render_clickable_generic(ctx: _Ctx) -> str:
    """Innermost ``generic [cursor=pointer]`` — promoted as a clickable atom."""
    inner = ((ctx.value + " ") if ctx.value else "") + _kids_md(
        ctx.children, ctx.depth, flow=True
    ).strip()
    inner_text = inner.strip()
    if inner_text:
        return f'clickable "{inner_text}"{ctx.ref_tag}'
    return f"clickable{ctx.ref_tag}"


def _render_grouping(ctx: _Ctx) -> str:
    """Form / search / tablist / menu containers.

    Flatten transparent descendants into a flat list of leaves, then emit each
    as its own paragraph. Avoids indent inversion from arbitrary DOM-wrapper
    depth (Google Flights' nested form generics, Wikipedia's search wrapper).
    Consecutive plain-text leaves combine into one paragraph; atoms keep
    their own. Counts leaves *after* flattening so a single-child wrapper
    can't mask a real multi-control region.
    """
    raw: list[tuple[str, bool]] = []
    _flatten_to_leaves(ctx.children, ctx.depth, raw)
    if not raw:
        return ""
    if len(raw) == 1:
        leading = (ctx.value + " ") if ctx.value else ""
        return leading + raw[0][0]
    leaves: list[str] = []
    buf: list[str] = []
    for text, is_plain in raw:
        if is_plain:
            buf.append(text)
        else:
            if buf:
                leaves.append(" ".join(buf))
                buf = []
            leaves.append(text)
    if buf:
        leaves.append(" ".join(buf))
    return "\n\n" + "\n\n".join(leaves) + "\n\n"


def _render_landmark(ctx: _Ctx) -> str:
    """Landmark roles (``banner``/``navigation``/``main``/…): emit children
    inline like a transparent container, but wrap with paragraph boundaries
    so adjacent landmarks render as distinct blocks rather than one big run.
    """
    inner = _kids_md(ctx.children, ctx.depth, flow=True).strip()
    return f"\n\n{inner}\n\n" if inner else ""


def _render_transparent(ctx: _Ctx) -> str:
    """Plain transparent containers (``generic``, ``region``, …)."""
    # A bare value-bearing transparent generic is almost always an aria-
    # labelled informational ``<div>`` — drop its ref unless actually clickable.
    effective_ref = ctx.ref_tag if (ctx.clickable or ctx.role != "generic") else ""
    if ctx.flow:
        leading = (ctx.value + " ") if ctx.value else ""
        return leading + _kids_md(ctx.children, ctx.depth, flow=True)
    return _bullet_block(ctx.value, ctx.children, ctx.depth, effective_ref)


# ── Composite helpers ───────────────────────────────────────────────────


# Punctuation/closers that should hug the preceding token (no inserted space).
_NO_SPACE_BEFORE = frozenset(".,;:!?)]}>")


def _kids_md(children: list[Any], depth: int, flow: bool = False) -> str:
    """Concat children's rendered fragments, inserting a space at boundaries
    where both sides are non-whitespace and the next side isn't punctuation.

    Prose pages have text nodes carrying their own whitespace ("is a ", " for
    managing data"); navigation menus and grouping containers don't (the
    visual spacing is CSS-only). Without this glue, adjacent buttons/links/
    boxes in a nav strip collide into one run like ``[X][Y]button "Z"``.
    Punctuation (``.``, ``,``, ``)`` …) must still hug the previous token, so
    we skip the space when the next fragment starts with a closer.
    """
    parts: list[str] = []
    for c in children:
        rendered = _render_md_node(c, depth, flow=flow)
        if not rendered:
            continue
        if (
            parts
            and parts[-1]
            and parts[-1][-1] not in " \t\n"
            and rendered[0] not in " \t\n"
            and rendered[0] not in _NO_SPACE_BEFORE
        ):
            parts.append(" ")
        parts.append(rendered)
    return "".join(parts)


def _bullet_block(
    value: str | None, children: list[Any], depth: int, ref_tag: str
) -> str:
    """Render a transparent/structural container as nested bullets.

    Collapses single-child wrappers so deep ``generic > generic > generic``
    chains don't pile up indentation. Each meaningful child becomes a bullet
    at ``depth``; descendants recurse at ``depth+1`` in bullet mode.
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
        # ``- ``), use as-is at depth+1 — don't double-wrap. If it's a block
        # form (pipe table, heading, fenced code), emit it as a standalone
        # block with blank-line boundaries so GitHub-Flavored Markdown parses it. Otherwise wrap
        # the inline content as a single bullet at ``depth``.
        cm = _render_md_node(c, depth + 1, flow=False).strip("\n")
        if not cm.strip():
            continue
        first_nonblank = cm.lstrip().split("\n", 1)[0].lstrip()
        if first_nonblank.startswith("- "):
            lines.append(cm)
        elif first_nonblank.startswith(("|", "#", "```")):
            # Standalone block (table / heading / fenced code) — keep it out
            # of the bullet wrapping so markdown parses it correctly.
            lines.append("\n" + cm + "\n")
        else:
            first, _, rest = cm.partition("\n")
            lines.append(f"{indent}- {first}" + (f"\n{rest}" if rest else ""))
    return "\n" + "\n".join(lines) + "\n"


def _flatten_to_leaves(
    nodes: list[Any], depth: int, out: list[tuple[str, bool]]
) -> None:
    """Walk transparent containers, collecting renderable leaves into ``out``.

    Each leaf is ``(text, is_plain)``:
      * ``is_plain=True``: a transparent container's scalar value — visible
        text with no actionable identity. Consecutive plain leaves combine
        into one bullet line by the caller (matches how a sighted user reads
        a row of UI text). A clickable transparent generic (cursor=pointer
        with a ref) is treated as an atom instead.
      * ``is_plain=False``: an actionable atom (link, button, form control,
        list, table, heading, …) rendered via the normal walk. Atoms always
        get their own bullet so the agent can target them.

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
                if ref and clickable:
                    out.append((f"{value} [ref={ref}]", False))  # atom
                else:
                    out.append((value, True))  # plain
            if kids:
                _flatten_to_leaves(kids, depth, out)
            continue
        # Non-transparent: render normally. Anything without a ``[ref=...]``
        # is pure inline text (e.g., a ``text`` leaf, an image with alt) →
        # plain so it combines with surrounding labels. Block-formatted roles
        # are always atoms regardless of ref so they don't merge into a run.
        cm = _render_md_node(c, depth, flow=True).strip()
        if cm:
            is_atom = role in _BLOCK_ATOM_ROLES or "[ref=" in cm
            out.append((cm, not is_atom))


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


# ── Dispatch table ──────────────────────────────────────────────────────
# Built after all handlers are defined. Role families (form controls, layout
# table parts) point to a shared handler. Fallback roles (transparent,
# clickable generic, grouping, unknown) are handled in ``_render_md_node``
# because they require role+state predicates rather than a simple key lookup.


_ROLE_HANDLERS: dict[str, Callable[[_Ctx], str]] = {
    # Block-level markdown forms.
    "heading":      _render_heading,
    "paragraph":    _render_paragraph,
    "code":         _render_code,
    "separator":    _render_separator,
    "list":         _render_list,
    "listitem":     _render_listitem,
    "table":        _render_table_node,
    "grid":         _render_table_node,
    # Inline atoms.
    "text":         _render_text,
    "link":         _render_link,
    "button":       _render_button,
    "img":          _render_img,
    "option":       _render_option,
    # Form controls (shared handler).
    **{r: _render_form_control for r in _FORM_CONTROL_ROLES},
    # Layout-table parts standalone (shared handler).
    **{r: _render_layout_part for r in _LAYOUT_PART_ROLES},
}


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
    ctx = _Ctx(
        role=role, name=name, ref=ref, state=state, clickable=clickable,
        children=children, value=value, ref_tag=f" [ref={ref}]" if ref else "",
        header=header, depth=depth, flow=flow,
    )

    handler = _ROLE_HANDLERS.get(role)
    if handler is not None:
        return handler(ctx)

    # Fallbacks needing role+state predicates rather than a simple key lookup.
    if (
        role == "generic"
        and clickable
        and ref is not None
        and not _has_click_target(children)
    ):
        return _render_clickable_generic(ctx)
    if role in _GROUPING_ROLES:
        return _render_grouping(ctx)
    # Strong landmarks always qualify; "named" ones only when they carry an
    # accessible name (avoids over-separation on sites that sprinkle
    # ``<section>`` / ``role="region"`` liberally).
    if role in _STRONG_LANDMARK_ROLES or (role in _NAMED_LANDMARK_ROLES and name):
        return _render_landmark(ctx)
    if role in _TRANSPARENT_ROLES:
        return _render_transparent(ctx)
    # Truly unknown role: inline-transparent.
    leading = (value + " ") if value else ""
    return leading + _kids_md(children, depth, flow=flow)


# ── Public API ──────────────────────────────────────────────────────────


def render_aria_markdown(aria_yaml: str) -> str:
    """Render an aria-snapshot YAML string as markdown with refs inlined."""
    try:
        tree = yaml.load(aria_yaml, Loader=_YamlLoader)
    except yaml.YAMLError:
        return ""
    if not isinstance(tree, list):
        return ""
    # Top-level defaults to flow=True (prose-friendly): paragraphs and headings
    # emit their own markdown, and page-wrapping generics inline normally.
    # Listitems/grouping switch to flow=False for their children so multi-child
    # generics fan out as nested bullets instead of producing a wall.
    text = "".join(_render_md_node(n, depth=0, flow=True) for n in tree)
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


