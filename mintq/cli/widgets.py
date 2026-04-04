"""Textual widgets for the mintq TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group
from rich.spinner import Spinner
from rich.text import Text
from pathlib import Path

from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Static

from mintq.cli.theme import ACCENT, ACCENT_BOLD

if TYPE_CHECKING:
    from rich.console import RenderableType

    from mintq.cli.agent import ChatResult


# ---------------------------------------------------------------------------
# Input with persistent history
# ---------------------------------------------------------------------------

_MAX_HISTORY_ENTRIES = 500


class HistoryInput(Input):
    """Input widget with file-backed command history (Up/Down arrows)."""

    BINDINGS = [
        Binding("up", "history_prev", "Previous command", priority=True),
        Binding("down", "history_next", "Next command", priority=True),
    ]

    def __init__(self, history_path: Path, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._history_path = history_path
        self._history: list[str] = []
        self._history_index: int = -1
        self._saved_input: str = ""
        self._load_history()

    def _load_history(self) -> None:
        if self._history_path.is_file():
            lines = self._history_path.read_text(encoding="utf-8").splitlines()
            self._history = lines[-_MAX_HISTORY_ENTRIES:]

    def _save_history(self) -> None:
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_path.write_text(
            "\n".join(self._history[-_MAX_HISTORY_ENTRIES:]) + "\n",
            encoding="utf-8",
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Automatically add submitted text to history."""
        self._add_to_history(event.value)

    def _add_to_history(self, text: str) -> None:
        """Append a command to history and persist."""
        stripped = text.strip()
        if not stripped:
            return
        if self._history and self._history[-1] == stripped:
            return
        self._history.append(stripped)
        self._history_index = -1
        self._saved_input = ""
        self._save_history()

    def action_history_prev(self) -> None:
        if not self._history:
            return
        if self._history_index == -1:
            self._saved_input = self.value
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        else:
            return
        self.value = self._history[self._history_index]
        self.cursor_position = len(self.value)

    def action_history_next(self) -> None:
        if self._history_index == -1:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.value = self._history[self._history_index]
        else:
            self._history_index = -1
            self.value = self._saved_input
        self.cursor_position = len(self.value)


# ---------------------------------------------------------------------------
# Simple message widgets
# ---------------------------------------------------------------------------


class BannerWidget(Static):
    """Displays the welcome banner."""

    DEFAULT_CSS = """
    BannerWidget {
        margin: 1 0;
    }
    """

    def __init__(self, *, model: str) -> None:
        from mintq.cli.display import build_banner

        super().__init__(build_banner(model=model))


class UserMessage(Static):
    """Displays a user input message."""

    DEFAULT_CSS = """
    UserMessage {
        margin: 1 0 0 0;
        padding: 0 1;
    }
    """

    def __init__(self, text: str) -> None:
        line = Text()
        line.append("┃ ", style=ACCENT_BOLD)
        line.append(text)
        super().__init__(line)


class SystemMessage(Static):
    """Displays system/command output."""

    DEFAULT_CSS = """
    SystemMessage {
        padding: 0 1;
    }
    """


class SpinnerWidget(Widget):
    """Simple animated spinner with a label."""

    DEFAULT_CSS = """
    SpinnerWidget {
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self, label: str = "Loading...") -> None:
        super().__init__()
        self._spinner = Spinner("dots", text=Text(label, style="dim"), style=ACCENT)

    def on_mount(self) -> None:
        self.set_interval(1 / 12, self.refresh)

    def render(self) -> RenderableType:
        return self._spinner


# ---------------------------------------------------------------------------
# Agent progress widget (implements ProgressSink)
# ---------------------------------------------------------------------------


class AgentProgressWidget(Widget):
    """Shows agent execution progress with tool steps and streaming text."""

    DEFAULT_CSS = """
    AgentProgressWidget {
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._steps: list[tuple[str, str, str]] = []
        self._streaming_text = ""
        self._status_text: str | None = "Thinking..."
        # Persistent spinner instances so animation state survives across renders.
        self._status_spinner = Spinner("dots", text=Text("Thinking...", style="dim"), style=ACCENT)
        self._tool_spinner = Spinner("dots", style="dim")

    def on_mount(self) -> None:
        self.set_interval(1 / 12, self.refresh)

    def render(self) -> RenderableType:
        parts: list[RenderableType] = []

        has_running = False
        for status, _name, label in self._steps:
            if status == "running":
                has_running = True
                self._tool_spinner.text = Text(label, style="dim")
                parts.append(self._tool_spinner)
            else:
                line = Text()
                line.append("→ ", style="dim")
                line.append(label, style="dim")
                parts.append(line)

        if self._status_text and not has_running:
            self._status_spinner.text = Text(self._status_text, style="dim")
            parts.append(self._status_spinner)

        if self._streaming_text:
            display = self._streaming_text
            if len(display) > 500:
                display = "..." + display[-497:]
            parts.append(Text())
            parts.append(Text(display, style="dim"))

        return Group(*parts) if parts else Text()

    # ProgressSink interface

    def start(self) -> None:
        pass

    def finish(self) -> None:
        self._streaming_text = ""
        self._refresh()

    def tool_start(self, name: str, args_summary: str) -> None:
        if self._status_text and self._status_text != "Thinking...":
            self._steps.append(("done", "__status__", self._status_text))
        label = f"{name}({args_summary})" if args_summary else name
        self._steps.append(("running", name, label))
        self._streaming_text = ""
        self._status_text = None
        self._refresh()

    def tool_end(self, name: str, result_summary: str) -> None:
        for i in range(len(self._steps) - 1, -1, -1):
            if self._steps[i][1] == name and self._steps[i][0] == "running":
                label = self._steps[i][2]
                self._steps[i] = ("done", name, f"{label} → {result_summary}")
                break
        self._status_text = "Thinking..."
        self._refresh()

    def text_delta(self, delta: str) -> None:
        self._streaming_text += delta
        self._status_text = None
        self._refresh()

    def set_status(self, text: str) -> None:
        self._status_text = text
        self._refresh()

    def _refresh(self) -> None:
        try:
            self.refresh()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Agent result widget with interactive tabs
# ---------------------------------------------------------------------------


class AgentResultWidget(Widget):
    """Displays an agent result with interactive tab switching."""

    DEFAULT_CSS = """
    AgentResultWidget {
        padding: 0 1;
        height: auto;
        border-left: blank;
    }

    AgentResultWidget:focus-within {
        border-left: thick $accent;
    }

    AgentResultWidget .tab-bar {
        height: 1;
        margin: 0 0 1 0;
    }

    AgentResultWidget .tab-active {
        background: $accent;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }

    AgentResultWidget .tab-inactive {
        color: $text-muted;
        padding: 0 1;
    }
    """

    current_tab: reactive[int] = reactive(0, init=False)

    def __init__(self, result: ChatResult, width: int = 80) -> None:
        super().__init__()
        from mintq.cli.display import build_result_views

        self._ordered_keys, self._views = build_result_views(result, width)
        self._content = Static(id="result-content")
        self._tab_labels: list[Static] = []
        self._mounted = False

    @property
    def has_tabs(self) -> bool:
        return len(self._ordered_keys) > 1

    def compose(self) -> object:
        if self.has_tabs:
            self._tab_labels = []
            labels: list[Static] = []
            for i, key in enumerate(self._ordered_keys):
                cls = "tab-active" if i == 0 else "tab-inactive"
                label_widget = Static(f" {key} ", classes=cls)
                label_widget._tab_index = i  # type: ignore[attr-defined]
                self._tab_labels.append(label_widget)
                labels.append(label_widget)

            hint = Static(" ←/→ switch ", classes="tab-inactive")
            labels.append(hint)
            yield Horizontal(*labels, classes="tab-bar")

        yield self._content

    def on_mount(self) -> None:
        self._mounted = True
        self._update_content()

    def watch_current_tab(self) -> None:
        if not self._mounted:
            return
        self._update_content()
        self._update_tab_styles()

    def _update_tab_styles(self) -> None:
        for i, label in enumerate(self._tab_labels):
            label.remove_class("tab-active", "tab-inactive")
            label.add_class("tab-active" if i == self.current_tab else "tab-inactive")

    def _update_content(self) -> None:
        if not self._ordered_keys:
            self._content.update(Text("No results to display.", style="dim"))
            return
        idx = min(self.current_tab, len(self._ordered_keys) - 1)
        key = self._ordered_keys[idx]
        renderable = self._views.get(key, Text(""))
        self._content.update(renderable)

    def on_click(self, event: object) -> None:
        """Handle clicks on tab labels."""
        from textual.events import Click

        assert isinstance(event, Click)
        widget = self.app.get_widget_at(event.screen_x, event.screen_y)[0]
        if hasattr(widget, "_tab_index"):
            self.current_tab = widget._tab_index  # type: ignore[attr-defined]

    def action_next_tab(self) -> None:
        if self._ordered_keys:
            self.current_tab = (self.current_tab + 1) % len(self._ordered_keys)

    def action_prev_tab(self) -> None:
        if self._ordered_keys:
            self.current_tab = (self.current_tab - 1) % len(self._ordered_keys)

    can_focus = True

    BINDINGS = [
        ("right", "next_tab", "Next tab"),
        ("left", "prev_tab", "Previous tab"),
        ("tab", "next_tab", "Next tab"),
        ("shift+tab", "prev_tab", "Previous tab"),
        ("up", "focus_prev_result", "Previous result"),
        ("down", "focus_next_result", "Next result"),
        ("k", "focus_prev_result", "Previous result"),
        ("j", "focus_next_result", "Next result"),
        ("escape", "focus_input", "Back to input"),
        ("i", "focus_input", "Back to input"),
    ]

    def action_focus_prev_result(self) -> None:
        """Focus the previous AgentResultWidget."""
        results = list(self.app.query(AgentResultWidget))
        try:
            idx = results.index(self)
        except ValueError:
            return
        if idx > 0:
            results[idx - 1].focus()
            results[idx - 1].scroll_visible()

    def action_focus_next_result(self) -> None:
        """Focus the next AgentResultWidget."""
        results = list(self.app.query(AgentResultWidget))
        try:
            idx = results.index(self)
        except ValueError:
            return
        if idx < len(results) - 1:
            results[idx + 1].focus()
            results[idx + 1].scroll_visible()

    def action_focus_input(self) -> None:
        """Return focus to the input bar."""
        self.app.query_one("#input-bar").focus()
