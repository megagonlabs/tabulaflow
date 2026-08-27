"""Streaming, selectable Markdown widgets for agent answers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from rich.text import Text

from textual._compositor import Compositor
from textual.content import Content, Span
from textual.geometry import Size
from textual.highlight import highlight
from textual.strip import Strip
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown, Static
from textual.widgets._markdown import MarkdownFence, MarkdownTable, MarkdownTableContent

from tabulaflow.app.theme import (
    CODE_FUNCTION,
    CODE_TEXT,
    TabulaflowCodeHighlightTheme,
)

if TYPE_CHECKING:
    from textual.selection import Selection


class _MarkdownStream(Protocol):
    async def write(self, markdown_fragment: str) -> None: ...

    async def stop(self) -> None: ...


def _visible_text_for_inline_token(token: Token) -> str:
    """Plain text contribution of a markdown inline token."""
    if token.type == "text":
        return re.sub(r"\s+", " ", token.content)
    if token.type == "code_inline":
        return token.content
    if token.type == "hardbreak":
        return "\n"
    if token.type == "softbreak":
        return " "
    if token.children is None:
        return ""
    return "".join(_visible_text_for_inline_token(child) for child in token.children)


def _render_interactive_markdown_as_plain_text(markdown: MarkdownIt) -> None:
    """Render interactive markdown inline tokens as visible plain text.

    Textual attaches click metadata to markdown links and images, but terminal
    link support is inconsistent. Keep destinations copyable and terminal-
    detectable by removing interactive tokens and rendering explicit
    destinations as ``label (url)``. Autolinks and labels that already equal the
    destination render as just their visible label.
    """

    def replace_interactive_tokens(state: StateCore) -> None:
        for token in state.tokens:
            if token.type != "inline" or token.children is None:
                continue

            children: list[Token] = []
            in_link = False
            href = ""
            is_autolink = False
            label_parts: list[str] = []
            for child in token.children:
                if child.type == "link_open":
                    href = str(child.attrs.get("href", ""))
                    is_autolink = child.markup == "autolink" or child.info == "auto"
                    label_parts = []
                    in_link = True
                    continue

                if child.type == "image":
                    label = _visible_text_for_inline_token(child)
                    src = str(child.attrs.get("src", ""))
                    image_text = Token("text", "", 0)
                    image_text.content = label
                    if src and label != src:
                        image_text.content = f"{label} ({src})" if label else src
                    if in_link:
                        label_parts.append(image_text.content)
                    children.append(image_text)
                    continue

                if child.type == "link_close" and in_link:
                    label = "".join(label_parts)
                    if href and not is_autolink and label != href:
                        visible_destination = Token("text", "", 0)
                        visible_destination.content = f" ({href})"
                        children.append(visible_destination)
                    in_link = False
                    continue

                if in_link:
                    label_parts.append(_visible_text_for_inline_token(child))
                children.append(child)

            token.children = children

    markdown.core.ruler.after(
        "inline",
        "render_interactive_markdown_as_plain_text",
        replace_interactive_tokens,
    )


def _make_agent_markdown_parser() -> MarkdownIt:
    # Keep GFM-style strikethrough delimiters visible in the terminal instead of
    # emitting a Rich/Textual ``strike`` style. Terminal support for strikethrough
    # is inconsistent, so rendering ``~~text~~`` literally is more predictable in
    # the TUI.
    markdown = MarkdownIt("commonmark", {"html": False}).enable(["table"]).disable("hr")
    _render_interactive_markdown_as_plain_text(markdown)
    return markdown


class AgentMarkdownFence(MarkdownFence):
    @classmethod
    def highlight(cls, code: str, language: str, ansi: bool = False, dark: bool = False) -> Content:
        if ansi:
            return super().highlight(code, language, ansi=ansi, dark=dark)
        content = highlight(code, language=language or None, theme=TabulaflowCodeHighlightTheme)
        spans = [
            Span(span.start, span.end, CODE_TEXT) if str(span.style) == "$text" else span for span in content.spans
        ]
        return Content(content.plain, spans, content.cell_length, strip_control_codes=False)


class AgentMarkdownTableContent(MarkdownTableContent):
    """Markdown table content without per-cell hover tooltips."""

    def _clear_cell_tooltips(self) -> None:
        for cell in self.query(".cell, .header"):
            cell.tooltip = None

    def on_mount(self) -> None:
        super().on_mount()
        self._clear_cell_tooltips()

    def _update_content(self, headers: list[Content], rows: list[list[Content]]) -> None:
        super()._update_content(headers, rows)
        self._clear_cell_tooltips()

    async def _update_rows(self, updated_rows: list[list[Content]]) -> None:
        await super()._update_rows(updated_rows)
        self._clear_cell_tooltips()


class AgentMarkdownTable(MarkdownTable):
    def compose(self) -> ComposeResult:
        headers, rows = self._get_headers_and_rows()
        self._headers = headers
        self._rows = rows
        yield AgentMarkdownTableContent(headers, rows)


class AgentTextBlock(Markdown):
    """The agent's natural-language answer, streamed into its own widget.

    ``AgentProgressWidget`` mounts one as a sibling for the final answer;
    mid-turn narration arrives as a separate ``NarrationDelta`` the app doesn't
    handle, so it never reaches here.
    """

    BULLETS = ["- "]
    BLOCKS = {
        **Markdown.BLOCKS,
        "fence": AgentMarkdownFence,
        "code_block": AgentMarkdownFence,
        "table_open": AgentMarkdownTable,
    }

    DEFAULT_CSS = f"""
    AgentTextBlock {{
        padding: 0 1;
        margin: 1 0 0 0;
        height: auto;
    }}

    AgentTextBlock MarkdownHeader {{
        color: $foreground;
        margin: 1 0 1 0;
    }}

    AgentTextBlock MarkdownH1,
    AgentTextBlock MarkdownH2,
    AgentTextBlock MarkdownH3,
    AgentTextBlock MarkdownH4,
    AgentTextBlock MarkdownH5,
    AgentTextBlock MarkdownH6 {{
        background: transparent;
        color: $foreground;
        content-align: left middle;
        text-style: bold;
    }}

    AgentTextBlock MarkdownParagraph {{
        margin: 0 0 1 0;
    }}

    AgentTextBlock MarkdownBulletList Horizontal > Vertical > MarkdownParagraph,
    AgentTextBlock MarkdownOrderedList Horizontal > Vertical > MarkdownParagraph {{
        margin: 0;
    }}

    AgentTextBlock MarkdownBlockQuote {{
        background: transparent;
        border-left: vkey $foreground;
        margin: 1 0;
        padding: 0 1;
    }}

    AgentTextBlock MarkdownFence {{
        background: transparent;
        color: {CODE_TEXT};
        margin: 0 0 1 2;
        overflow: hidden hidden;
        padding: 0;
        scrollbar-size-horizontal: 0;
    }}

    AgentTextBlock MarkdownFence > Label {{
        padding: 0;
        text-wrap: wrap;
        width: 1fr;
    }}

    AgentTextBlock MarkdownBlock > .code_inline,
    AgentTextBlock MarkdownBlock:dark > .code_inline,
    AgentTextBlock MarkdownBlock:light > .code_inline {{
        background: transparent;
        color: {CODE_FUNCTION};
        text-style: none;
    }}

    AgentTextBlock MarkdownBullet,
    AgentTextBlock MarkdownTableContent > .header {{
        color: $foreground;
    }}

    AgentTextBlock MarkdownTableContent {{
        keyline: thin $foreground;
    }}

    AgentTextBlock MarkdownTableContent > .cell,
    AgentTextBlock MarkdownTableContent > .header {{
        padding: 0 1;
    }}
    """

    def __init__(self, markdown: str | None = None) -> None:
        super().__init__(markdown, parser_factory=_make_agent_markdown_parser, open_links=False)
        self._stream: _MarkdownStream | None = None

    async def write_delta(self, delta: str) -> None:
        if self._stream is None:
            self._stream = Markdown.get_stream(self)
        await self._stream.write(delta)

    async def replace_markdown(self, markdown: str) -> None:
        await self.stop_stream()
        await self.update(markdown)

    async def stop_stream(self) -> None:
        if self._stream is None:
            return
        stream = self._stream
        self._stream = None
        await stream.stop()

    async def freeze(self) -> "FrozenAgentTextBlock | None":
        """Replace the live Markdown widget tree with a lightweight snapshot.

        Textual's ``Markdown`` expands each completed answer into many mounted
        child widgets. Keeping all those old children live makes unrelated input
        updates slower as a conversation grows. Completed answers are static, so
        snapshot Textual's own rendered strips and replay them from a single
        widget without adding descendants to the Textual DOM.
        """
        await self.stop_stream()
        parent = self.parent
        if not isinstance(parent, Widget) or not self.is_mounted:
            return None
        children = self.walk_children(with_self=False)
        if children and not any(
            child.size.width > 0 and child.size.height > 0 for child in children if isinstance(child, Widget)
        ):
            self.refresh(layout=True)
            return None
        content_width = (
            self.size.width
            or self.content_size.width
            or self.container_size.width
            or parent.content_size.width
            or parent.size.width
            or self.app.size.width
        )
        if content_width <= 0:
            return None
        width = content_width + self.styles.gutter.width
        height = max(
            self.size.height,
            self.get_content_height(Size(content_width, self.app.size.height), self.app.size, content_width),
        )
        if height <= 0:
            return None
        compositor = Compositor()
        compositor.reflow(self, Size(width, height))
        strips = [Strip.join(list(line)) for line in compositor.render_full_update().strips]
        frozen = FrozenAgentTextBlock(strips, width)
        self.screen.clear_selection()
        with self.app.batch_update():
            await parent.mount(frozen, after=self)
            await self.remove()
        return frozen


def _strips_to_text(strips: list[Strip]) -> Text:
    """Convert pre-rendered strips into one styled, pre-line-broken text object."""
    out = Text(no_wrap=True, overflow="crop")
    for line_no, strip in enumerate(strips):
        if line_no:
            out.append("\n")
        remaining = len(strip.text.rstrip())
        for segment in strip._segments:
            if remaining <= 0:
                break
            text = segment.text[:remaining]
            out.append(text, segment.style)
            remaining -= len(text)
    return out


class FrozenAgentTextBlock(Static):
    """Lightweight snapshot of a completed assistant answer."""

    ALLOW_SELECT = True

    DEFAULT_CSS = """
    FrozenAgentTextBlock {
        margin: 1 0 0 0;
        height: auto;
    }
    """

    def __init__(self, strips: list[Strip], width: int) -> None:
        text = _strips_to_text(strips)
        super().__init__(text, markup=False)
        self._selection_text = f"{text.plain}\n"
        self._width = width
        self._height = len(strips)

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return min(self._width, container.width) if container.width else self._width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return self._height

    def get_selection(self, selection: "Selection") -> tuple[str, str] | None:
        return selection.extract(self._selection_text), "\n"


_UNLISTED_TOOL = "show_artifacts"
