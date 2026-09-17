"""Inline choice control for command workflows."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static

from tabulaflow.app.tui.theme import KEY_HINT


class InlineChoiceSelector(Vertical):
    """Searchable inline selector for a finite list of string options."""

    can_focus = True

    DEFAULT_CSS = """
    InlineChoiceSelector {
        height: auto;
        margin: 1 2 0 1;
        padding: 0 2;
        background: $focus-surface;
        border: round #6a737d;
    }

    InlineChoiceSelector #choice-title {
        height: 1;
        margin-bottom: 1;
    }

    InlineChoiceSelector #choice-options {
        height: auto;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
        Binding("up", "move(-1)", "Previous", show=False, priority=True),
        Binding("down", "move(1)", "Next", show=False, priority=True),
        Binding("enter", "choose", "Choose", show=False, priority=True),
        Binding("backspace", "erase_filter", "Edit filter", show=False, priority=True),
    ]

    class Selected(Message):
        """An option was selected."""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    class Cancelled(Message):
        """Selection was cancelled."""

    def __init__(
        self,
        title: str,
        options: tuple[str, ...],
        *,
        confirm_label: str = "Select",
        visible_rows: int = 8,
    ) -> None:
        if not options:
            raise ValueError("InlineChoiceSelector requires at least one option")
        if visible_rows < 1:
            raise ValueError("visible_rows must be positive")
        super().__init__()
        self._title = title
        self._options = options
        self._visible_options = options
        self._confirm_label = confirm_label
        self._visible_rows = visible_rows
        self._cursor = 0
        self._filter = ""

    def compose(self) -> ComposeResult:
        yield Static(id="choice-title")
        yield Static(id="choice-options")

    def on_mount(self) -> None:
        self._refresh()
        self.focus()

    def on_resize(self) -> None:
        self._refresh_header()

    def on_key(self, event: events.Key) -> None:
        if not event.is_printable or event.character is None:
            return
        self._filter += event.character
        self._apply_filter()
        event.stop()
        event.prevent_default()

    def action_move(self, delta: int) -> None:
        if not self._visible_options:
            return
        self._cursor = max(0, min(len(self._visible_options) - 1, self._cursor + delta))
        self._refresh()

    def action_choose(self) -> None:
        if self._visible_options:
            self.post_message(self.Selected(self._visible_options[self._cursor]))

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    def action_erase_filter(self) -> None:
        if not self._filter:
            return
        self._filter = self._filter[:-1]
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self._filter.casefold()
        self._visible_options = tuple(option for option in self._options if query in option.casefold())
        self._cursor = 0
        self._refresh()

    def _refresh(self) -> None:
        self._refresh_header()
        visible = len(self._visible_options)
        if not visible:
            self.query_one("#choice-options", Static).update(Text("  No matching options", style="dim"))
            return

        start = max(0, min(self._cursor - self._visible_rows // 2, visible - self._visible_rows))
        rows = Text()
        if start > 0:
            rows.append(f"  ↑ {start} more\n", style="dim")
        for index in range(start, min(start + self._visible_rows, visible)):
            is_cursor = index == self._cursor
            rows.append("  ")
            rows.append("❯ " if is_cursor else "  ", style=KEY_HINT if is_cursor else "")
            rows.append(self._visible_options[index], style="bold" if is_cursor else "")
            rows.append("\n")
        remaining = visible - min(start + self._visible_rows, visible)
        if remaining:
            rows.append(f"  ↓ {remaining} more", style="dim")
        elif rows.plain.endswith("\n"):
            rows.rstrip()
        self.query_one("#choice-options", Static).update(rows)

    def _refresh_header(self) -> None:
        title_widget = self.query_one("#choice-title", Static)
        available = title_widget.size.width or 80
        title = Text(self._title, style="bold dim")
        if self._filter:
            title.append(" · ", style="dim")
            title.append(f"“{self._filter}”", style="bold")

        hint = Text(no_wrap=True)
        hint.append("↑↓", style=KEY_HINT)
        hint.append(" Move · ", style="dim")
        hint.append("Type", style=KEY_HINT)
        hint.append(" Filter · ", style="dim")
        hint.append("Enter", style=KEY_HINT)
        hint.append(f" {self._confirm_label} · ", style="dim")
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Cancel", style="dim")

        title_width = max(0, available - hint.cell_len - 1)
        if title_width:
            title.truncate(title_width, overflow="ellipsis")
        else:
            title = Text()

        header = Text(no_wrap=True, overflow="crop")
        header.append_text(title)
        if title_width:
            header.append(" " * (available - title.cell_len - hint.cell_len))
        header.append_text(hint)
        title_widget.update(header)
