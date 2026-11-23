"""Provider selection and API-key screens for model configuration."""

from __future__ import annotations

import os

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from tabulaflow.app.credentials import APIKeyStore, InvalidCredentialStoreError, activate_api_key, mask_api_key
from tabulaflow.app.providers import PROVIDER_SPECS, ProviderSpec
from tabulaflow.app.tui.theme import ACCENT_BOLD, KEY_HINT


def _selection_window(cursor: int, row_count: int, height: int) -> tuple[int, int, bool, bool]:
    available = max(1, height)
    for capacity in range(min(row_count, available), 0, -1):
        start = max(0, min(cursor - capacity // 2, row_count - capacity))
        end = start + capacity
        show_above = start > 0
        show_below = end < row_count
        if capacity + show_above + show_below <= available:
            return start, end, show_above, show_below
    start = cursor
    end = start + 1
    return start, end, start > 0 and available > 1, end < row_count and available > 2


class ProviderPickerScreen(Screen[ProviderSpec | None]):
    """Full-screen type-to-filter provider picker."""

    can_focus = True

    DEFAULT_CSS = """
    ProviderPickerScreen { background: $background; }
    ProviderPickerScreen #provider-picker { height: 1fr; padding: 1 3; }
    ProviderPickerScreen #provider-picker-title { height: auto; margin-bottom: 1; }
    ProviderPickerScreen #provider-options { height: 1fr; padding: 0 0 1 0; }
    ProviderPickerScreen #provider-picker-hint { dock: bottom; padding: 0 1; color: #f5f5f5; background: #2a2a2a; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Back", show=False, priority=True),
        Binding("up", "move(-1)", "Previous", show=False, priority=True),
        Binding("down", "move(1)", "Next", show=False, priority=True),
        Binding("enter", "select", "Select", show=False, priority=True),
        Binding("backspace", "erase_filter", "Edit filter", show=False, priority=True),
    ]

    def __init__(self, current: str) -> None:
        super().__init__()
        self._providers = tuple(sorted(PROVIDER_SPECS, key=lambda provider: provider.id != current))
        self._visible = self._providers
        self._cursor = next(
            (index for index, provider in enumerate(self._providers) if provider.id == current),
            0,
        )
        self._filter = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="provider-picker"):
            yield Static(id="provider-picker-title")
            yield Static(id="provider-options")
        yield Static(id="provider-picker-hint")

    def on_mount(self) -> None:
        self.focus()
        self._refresh()

    def on_resize(self) -> None:
        self.call_after_refresh(self._refresh)

    def on_key(self, event: events.Key) -> None:
        if not event.is_printable or event.character is None:
            return
        self._filter += event.character
        self._apply_filter()
        event.stop()
        event.prevent_default()

    def action_move(self, delta: int) -> None:
        if self._visible:
            self._cursor = max(0, min(len(self._visible) - 1, self._cursor + delta))
            self._refresh()

    def action_select(self) -> None:
        if self._visible:
            self.dismiss(self._visible[self._cursor])

    def action_erase_filter(self) -> None:
        if self._filter:
            self._filter = self._filter[:-1]
            self._apply_filter()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _apply_filter(self) -> None:
        query = self._filter.casefold()
        self._visible = tuple(
            provider
            for provider in self._providers
            if query in provider.name.casefold() or query in provider.id.casefold()
        )
        self._cursor = 0
        self._refresh()

    def _refresh(self) -> None:
        title = Text("Choose provider", style="bold")
        if self._filter:
            title.append(" · ", style="dim")
            title.append(f"“{self._filter}”", style="bold")
        else:
            title.append(" · Type to search", style="dim")
        self.query_one("#provider-picker-title", Static).update(title)

        options_widget = self.query_one("#provider-options", Static)
        options = Text(overflow="ellipsis", no_wrap=True)
        if self._visible:
            start, end, show_above, show_below = _selection_window(
                self._cursor,
                len(self._visible),
                options_widget.content_size.height,
            )
            if show_above:
                options.append(f"  ↑ {start} more\n", style="dim")
            for index in range(start, end):
                provider = self._visible[index]
                selected = index == self._cursor
                options.append("❯ " if selected else "  ", style=ACCENT_BOLD if selected else "")
                options.append(provider.name, style=ACCENT_BOLD if selected else "")
                options.append("\n")
            if show_below:
                options.append(f"  ↓ {len(self._visible) - end} more", style="dim")
        else:
            options.append("  No matching providers", style="dim")
        options_widget.update(options)
        self.query_one("#provider-picker-hint", Static).update(
            Text.assemble(("Esc", KEY_HINT), (" Back    ", "dim"), ("Enter", KEY_HINT), (" Select", "dim"))
        )


class APIKeyScreen(Screen[bool | None]):
    """Select an existing provider key or paste and save a new one."""

    can_focus = True

    DEFAULT_CSS = """
    APIKeyScreen { background: $background; }
    APIKeyScreen #api-key-body { height: 1fr; padding: 1 3; }
    APIKeyScreen #api-key-title { height: auto; margin-bottom: 1; }
    APIKeyScreen #api-key-options { height: auto; }
    APIKeyScreen #api-key-paste { height: auto; }
    APIKeyScreen #api-key-paste-label { width: auto; height: 1; }
    APIKeyScreen #api-key-input { height: 3; width: 1fr; max-width: 64; margin: 0 0 0 2; border: round #6a737d; padding: 0 1; background: transparent; }
    APIKeyScreen #api-key-input:focus { border: round #5FAF87; background: transparent; }
    APIKeyScreen #api-key-status { height: auto; color: $text-muted; }
    APIKeyScreen #api-key-hint { dock: bottom; padding: 0 1; color: #f5f5f5; background: #2a2a2a; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Back", show=False, priority=True),
        Binding("up", "move(-1)", "Previous", show=False, priority=True),
        Binding("down", "move(1)", "Next", show=False, priority=True),
        Binding("enter", "select", "Select", show=False, priority=True),
    ]

    def __init__(self, provider: ProviderSpec, *, credential_store: APIKeyStore | None = None) -> None:
        super().__init__()
        self._provider = provider
        self._store = credential_store or APIKeyStore()
        self._editing_key = False
        self._cursor = 0
        self._error = ""
        self._options: list[tuple[str, str | None, str | None]] = []
        for name in provider.api_key_vars:
            if key := os.getenv(name, "").strip():
                self._options.append((f"Use detected {name} ({mask_api_key(key) or '••••'})", name, key))
        try:
            saved = self._store.load()
        except InvalidCredentialStoreError as error:
            saved = {}
            self._error = str(error)
        for name in provider.api_key_vars:
            saved_key = saved.get(name)
            if saved_key and not any(option[1] == name and option[2] == saved_key for option in self._options):
                self._options.append((f"Use saved {name} ({mask_api_key(saved_key) or '••••'})", name, saved_key))
        self._options.append(("Paste API key", None, None))

    def compose(self) -> ComposeResult:
        with Vertical(id="api-key-body"):
            yield Static(id="api-key-title")
            yield Static(id="api-key-options")
            with Vertical(id="api-key-paste"):
                yield Static(id="api-key-paste-label")
                yield Input(placeholder="API key", password=True, id="api-key-input")
            yield Static(id="api-key-status")
        yield Static(id="api-key-hint")

    def on_mount(self) -> None:
        self._sync_focus()

    def action_move(self, delta: int) -> None:
        cursor = max(0, min(len(self._options) - 1, self._cursor + delta))
        if cursor != self._cursor:
            self._cursor = cursor
            self._error = ""
            self._sync_focus()

    def action_select(self) -> None:
        _, name, key = self._options[self._cursor]
        if name is None:
            if self._editing_key:
                self._save_key(self.query_one("#api-key-input", Input).value)
            else:
                self._sync_focus()
            return
        assert key is not None
        activate_api_key(name, key, store=self._store)
        self.dismiss(True)

    def _sync_focus(self) -> None:
        self._editing_key = self._cursor == len(self._options) - 1
        self._refresh()
        if self._editing_key:
            self.query_one("#api-key-input", Input).focus()
        else:
            self.focus()

    def action_cancel(self) -> None:
        if self._editing_key:
            self._editing_key = False
            self._error = ""
            input_widget = self.query_one("#api-key-input", Input)
            input_widget.value = ""
            self._refresh()
            self.focus()
        else:
            self.dismiss(None)

    def _save_key(self, value: str) -> None:
        key = value.strip()
        if not key:
            self._error = "API key cannot be empty."
            self._refresh()
            return
        name = self._provider.api_key_vars[0]
        try:
            activate_api_key(name, key, persist=True, store=self._store)
        except (InvalidCredentialStoreError, OSError):
            self._error = "Could not save the API key. Check the credential file and try again."
            self._refresh()
            return
        self.dismiss(True)

    def _refresh(self) -> None:
        self.query_one("#api-key-title", Static).update(Text(f"Connect {self._provider.name}", style="bold"))
        options = Text()
        connection_option_count = len(self._options) - 1
        for index, (label, name, _) in enumerate(self._options):
            if name is None:
                continue
            selected = index == self._cursor and not self._editing_key
            options.append("❯ " if selected else "  ", style=ACCENT_BOLD if selected else "")
            options.append(label, style=ACCENT_BOLD if selected else "")
            if index + 1 < connection_option_count:
                options.append("\n\n")
        options_widget = self.query_one("#api-key-options", Static)
        options_widget.update(options)
        options_widget.display = connection_option_count > 0
        self.query_one("#api-key-paste").styles.margin = (1 if connection_option_count else 0, 0, 0, 0)
        paste_selected = self._cursor == len(self._options) - 1
        paste_label = Text()
        paste_label.append("❯ " if paste_selected else "  ", style=ACCENT_BOLD if paste_selected else "")
        paste_label.append("Paste API key", style=ACCENT_BOLD if paste_selected else "")
        self.query_one("#api-key-paste-label", Static).update(paste_label)
        self.query_one("#api-key-status", Static).update(Text(self._error, style="dim"))
        action = "Save" if self._editing_key else "Select"
        self.query_one("#api-key-hint", Static).update(
            Text.assemble(("Esc", KEY_HINT), (" Back    ", "dim"), ("Enter", KEY_HINT), (f" {action}", "dim"))
        )
