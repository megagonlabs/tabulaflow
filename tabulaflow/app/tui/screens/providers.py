"""Provider selection and API-key screens for model configuration."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from tabulaflow.app.config import EndpointConnection, normalize_endpoint_url
from tabulaflow.app.credentials import (
    APIKeyStore,
    InvalidCredentialStoreError,
    activate_api_key,
    activate_vllm_connection,
    mask_api_key,
)
from tabulaflow.app.model_catalog import (
    DEFAULT_VLLM_BASE_URL,
    VLLMDiscoveryResult,
    VLLMModelDiscovery,
    discover_vllm_models,
)
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
        self._current = current
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
                active = provider.id == self._current
                options.append("❯ " if selected else "  ", style=ACCENT_BOLD if selected else "")
                options.append("● " if active else "  ", style=ACCENT_BOLD if active else "")
                options.append(provider.name, style=ACCENT_BOLD if active else "bold" if selected else "")
                options.append("\n")
            if show_below:
                options.append(f"  ↓ {len(self._visible) - end} more", style="dim")
        else:
            options.append("  No matching providers", style="dim")
        options_widget.update(options)
        self.query_one("#provider-picker-hint", Static).update(
            Text.assemble(("Esc", KEY_HINT), (" Back    ", "dim"), ("Enter", KEY_HINT), (" Select", "dim"))
        )


@dataclass(frozen=True)
class APIKeySelection:
    """A credential source selected for the current provider."""

    variable: str
    source: Literal["environment", "saved"]


@dataclass(frozen=True)
class _ConnectionOption:
    label: str
    variable: str
    key: str
    source: Literal["environment", "saved"]


class APIKeyScreen(Screen[APIKeySelection | None]):
    """Select an existing provider key or paste and save a new one."""

    can_focus = True

    DEFAULT_CSS = """
    APIKeyScreen { background: $background; }
    APIKeyScreen #api-key-body { height: 1fr; padding: 1 3; }
    APIKeyScreen #api-key-title { height: auto; margin-bottom: 1; }
    APIKeyScreen #api-key-options { height: auto; }
    APIKeyScreen #api-key-paste { height: auto; }
    APIKeyScreen #api-key-paste-label { width: auto; height: 1; }
    APIKeyScreen #api-key-input { height: 3; width: 1fr; max-width: 64; margin: 0 0 0 4; border: round #6a737d; padding: 0 1; background: transparent; }
    APIKeyScreen #api-key-input:focus { border: round $foreground; background: transparent; }
    APIKeyScreen #api-key-status { height: auto; color: $text-muted; }
    APIKeyScreen #api-key-hint { dock: bottom; padding: 0 1; color: #f5f5f5; background: #2a2a2a; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Back", show=False, priority=True),
        Binding("up", "move(-1)", "Previous", show=False, priority=True),
        Binding("down", "move(1)", "Next", show=False, priority=True),
        Binding("enter", "select", "Select", show=False, priority=True),
    ]

    def __init__(
        self,
        provider: ProviderSpec,
        *,
        credential_store: APIKeyStore | None = None,
        preferred_saved_variable: str | None = None,
        environment_variables: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._provider = provider
        self._store = credential_store or APIKeyStore()
        self._preferred_saved_variable = preferred_saved_variable
        environment_variables = environment_variables or {}
        self._editing_key = False
        self._error = ""
        self._options: list[_ConnectionOption] = []
        for name in provider.api_key_vars:
            key = (
                environment_variables[name].strip()
                if name in environment_variables
                else os.getenv(name, "").strip()
            )
            if key:
                label = f"Use environment {name} ({mask_api_key(key) or '••••'})"
                self._options.append(_ConnectionOption(label, name, key, "environment"))
        try:
            saved = self._store.load()
        except InvalidCredentialStoreError as error:
            saved = {}
            self._error = str(error)
        for name in provider.api_key_vars:
            saved_key = saved.get(name)
            if saved_key:
                label = f"Use saved {name} ({mask_api_key(saved_key) or '••••'})"
                self._options.append(_ConnectionOption(label, name, saved_key, "saved"))
        self._cursor = self._active_option_index() or 0

    def _active_option_index(self) -> int | None:
        if self._preferred_saved_variable is not None:
            for index, option in enumerate(self._options):
                if option.source == "saved" and option.variable == self._preferred_saved_variable:
                    return index
        for index, option in enumerate(self._options):
            if option.source == "environment":
                return index
        return 0 if self._options else None

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
        cursor = max(0, min(len(self._options), self._cursor + delta))
        if cursor != self._cursor:
            self._cursor = cursor
            self._error = ""
            self._sync_focus()

    def action_select(self) -> None:
        if self._cursor == len(self._options):
            if self._editing_key:
                self._save_key(self.query_one("#api-key-input", Input).value)
            else:
                self._sync_focus()
            return
        option = self._options[self._cursor]
        activate_api_key(option.variable, option.key, store=self._store)
        self.dismiss(APIKeySelection(variable=option.variable, source=option.source))

    def _sync_focus(self) -> None:
        self._editing_key = self._cursor == len(self._options)
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
        self.dismiss(APIKeySelection(variable=name, source="saved"))

    def _refresh(self) -> None:
        self.query_one("#api-key-title", Static).update(Text(f"Connect {self._provider.name}", style="bold"))
        options = Text()
        active_index = self._active_option_index()
        for index, option in enumerate(self._options):
            selected = index == self._cursor and not self._editing_key
            active = index == active_index
            options.append("❯ " if selected else "  ", style=ACCENT_BOLD if selected else "")
            options.append("● " if active else "  ", style=ACCENT_BOLD if active else "")
            options.append(option.label, style=ACCENT_BOLD if active else "bold" if selected else "")
            if index + 1 < len(self._options):
                options.append("\n\n")
        options_widget = self.query_one("#api-key-options", Static)
        options_widget.update(options)
        options_widget.display = bool(self._options)
        self.query_one("#api-key-paste").styles.margin = (1 if self._options else 0, 0, 0, 0)
        paste_selected = self._cursor == len(self._options)
        paste_label = Text()
        paste_label.append("❯   " if paste_selected else "    ", style=ACCENT_BOLD if paste_selected else "")
        paste_label.append("Paste API key", style="bold" if paste_selected else "")
        self.query_one("#api-key-paste-label", Static).update(paste_label)
        self.query_one("#api-key-status", Static).update(Text(self._error, style="dim"))
        action = "Save" if self._editing_key else "Select"
        self.query_one("#api-key-hint", Static).update(
            Text.assemble(("Esc", KEY_HINT), (" Back    ", "dim"), ("Enter", KEY_HINT), (f" {action}", "dim"))
        )


@dataclass(frozen=True)
class VLLMConnectionSelection:
    """A validated vLLM endpoint selected for model use."""

    base_url: str
    api_key: str
    source: Literal["environment", "saved"]
    models: tuple[str, ...]


@dataclass(frozen=True)
class _EndpointOption:
    base_url: str
    api_key: str
    source: Literal["environment", "saved"]


class VLLMConnectionScreen(Screen[VLLMConnectionSelection | None]):
    """Connect to a vLLM endpoint and discover its models."""

    can_focus = True

    DEFAULT_CSS = """
    VLLMConnectionScreen { background: $background; }
    VLLMConnectionScreen #connection-body { height: 1fr; padding: 1 3; }
    VLLMConnectionScreen #connection-title { height: auto; margin-bottom: 1; }
    VLLMConnectionScreen #connection-options { height: auto; }
    VLLMConnectionScreen #connection-url-label, #connection-key-label { width: auto; height: 1; }
    VLLMConnectionScreen #connection-url-input, #connection-key-input {
        height: 3; width: 1fr; max-width: 80; margin: 0 0 0 4;
        border: round #6a737d; padding: 0 1; background: transparent;
    }
    VLLMConnectionScreen #connection-url-input:focus, #connection-key-input:focus {
        border: round $foreground; background: transparent;
    }
    VLLMConnectionScreen #connection-key { height: auto; margin-top: 1; }
    VLLMConnectionScreen #connection-status { height: auto; color: $text-muted; }
    VLLMConnectionScreen #connection-hint { dock: bottom; padding: 0 1; color: #f5f5f5; background: #2a2a2a; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Back", show=False, priority=True),
        Binding("up", "move(-1)", "Previous", show=False, priority=True),
        Binding("down", "move(1)", "Next", show=False, priority=True),
        Binding("enter", "select", "Connect", show=False, priority=True),
    ]

    def __init__(
        self,
        *,
        connection: EndpointConnection | None = None,
        discovery: VLLMModelDiscovery | None = None,
        discovery_loader: Callable[[str, str], Awaitable[VLLMDiscoveryResult]] | None = None,
        credential_store: APIKeyStore | None = None,
        environment_variables: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._connection = connection
        self._discovery = discovery or VLLMModelDiscovery()
        self._discovery_loader = discovery_loader or discover_vllm_models
        self._store = credential_store or APIKeyStore()
        environment_variables = environment_variables or {}
        environment_url = environment_variables.get("VLLM_BASE_URL", os.getenv("VLLM_BASE_URL", "")).strip()
        environment_key = environment_variables.get("VLLM_API_KEY", os.getenv("VLLM_API_KEY", "")).strip()
        self._options: list[_EndpointOption] = []
        if environment_url:
            self._options.append(_EndpointOption(environment_url, environment_key, "environment"))
        self._error = ""
        try:
            saved_key = self._store.get("VLLM_API_KEY") or ""
        except InvalidCredentialStoreError as error:
            saved_key = ""
            self._error = str(error)
        if connection is not None:
            self._options.append(_EndpointOption(connection.base_url, saved_key, "saved"))
        active_index = self._active_option_index()
        self._cursor = active_index if active_index is not None else len(self._options)
        self._show_api_key = False
        self._connecting = False
        self._pending_option: _EndpointOption | None = None
        self._initial_url = connection.base_url if connection is not None else DEFAULT_VLLM_BASE_URL

    def _active_option_index(self) -> int | None:
        source = self._connection.source if self._connection is not None else "environment"
        return next((index for index, option in enumerate(self._options) if option.source == source), None)

    def compose(self) -> ComposeResult:
        with Vertical(id="connection-body"):
            yield Static(Text("Connect vLLM", style="bold"), id="connection-title")
            yield Static(id="connection-options")
            with Vertical(id="connection-url"):
                yield Static(id="connection-url-label")
                yield Input(value=self._initial_url, id="connection-url-input")
            with Vertical(id="connection-key"):
                yield Static(id="connection-key-label")
                yield Input(placeholder="API key", password=True, id="connection-key-input")
            yield Static(id="connection-status")
        yield Static(id="connection-hint")

    def on_mount(self) -> None:
        self._sync_focus()

    def action_move(self, delta: int) -> None:
        if self._connecting:
            return
        cursor = max(0, min(len(self._options) + 1, self._cursor + delta))
        if cursor != self._cursor:
            self._cursor = cursor
            self._pending_option = None
            self._error = ""
            self._sync_focus()

    def action_select(self) -> None:
        if self._connecting:
            return
        if self._cursor == len(self._options) + 1 and not self._show_api_key:
            self._show_api_key = True
            self._error = ""
            self._sync_focus()
            return
        source: Literal["environment", "saved"]
        if self._pending_option is not None and self._show_api_key:
            base_url = self._pending_option.base_url
            api_key = self.query_one("#connection-key-input", Input).value.strip()
            source = "saved"
        elif self._cursor < len(self._options):
            option = self._options[self._cursor]
            base_url = option.base_url
            api_key = option.api_key
            source = option.source
            self._pending_option = option
        else:
            base_url = self.query_one("#connection-url-input", Input).value
            api_key = self.query_one("#connection-key-input", Input).value.strip() if self._show_api_key else ""
            source = "saved"
            self._pending_option = None
        try:
            base_url = normalize_endpoint_url(base_url)
        except ValueError as error:
            self._error = str(error)
            self._refresh()
            return
        self.run_worker(self._connect(base_url, api_key, source), exclusive=True)

    async def _connect(self, base_url: str, api_key: str, source: Literal["environment", "saved"]) -> None:
        self._connecting = True
        self._error = "Discovering models…"
        self._refresh()
        result = await self._discovery_loader(base_url, api_key)
        self._connecting = False
        if result.error is not None:
            self._error = result.error
            if result.authentication_required:
                self._show_api_key = True
                self._cursor = len(self._options) + 1
                self._error = "Authentication required. Enter an API key and retry."
            self._sync_focus()
            return
        try:
            activate_vllm_connection(
                base_url,
                api_key,
                persist_key=source == "saved",
                store=self._store,
            )
        except (InvalidCredentialStoreError, OSError):
            self._error = "Could not save the API key. Check the credential file and try again."
            self._sync_focus()
            return
        self._discovery.configure(base_url, api_key, result)
        self.dismiss(VLLMConnectionSelection(base_url, api_key, source, result.models))

    def _sync_focus(self) -> None:
        self._refresh()
        if self._cursor == len(self._options):
            self.query_one("#connection-url-input", Input).focus()
        elif self._cursor == len(self._options) + 1 and self._show_api_key:
            self.query_one("#connection-key-input", Input).focus()
        else:
            self.focus()

    def action_cancel(self) -> None:
        if not self._connecting:
            self.dismiss(None)

    def _refresh(self) -> None:
        options = Text(overflow="ellipsis", no_wrap=True)
        active_index = self._active_option_index()
        for index, option in enumerate(self._options):
            selected = index == self._cursor
            active = index == active_index
            label = f"Use {option.source} endpoint ({option.base_url})"
            options.append("❯ " if selected else "  ", style=ACCENT_BOLD if selected else "")
            options.append("● " if active else "  ", style=ACCENT_BOLD if active else "")
            options.append(label, style=ACCENT_BOLD if active else "bold" if selected else "")
            if index + 1 < len(self._options):
                options.append("\n\n")
        options_widget = self.query_one("#connection-options", Static)
        options_widget.update(options)
        options_widget.display = bool(self._options)
        self.query_one("#connection-url").styles.margin = (1 if self._options else 0, 0, 0, 0)

        url_selected = self._cursor == len(self._options)
        url_label = Text("❯   " if url_selected else "    ", style=ACCENT_BOLD if url_selected else "")
        url_label.append("Server URL", style="bold" if url_selected else "")
        self.query_one("#connection-url-label", Static).update(url_label)
        self.query_one("#connection-url-input", Input).disabled = self._connecting

        key_selected = self._cursor == len(self._options) + 1
        key_label = Text("❯   " if key_selected else "    ", style=ACCENT_BOLD if key_selected else "")
        key_label.append(
            "API key (optional)" if self._show_api_key else "Add API key (optional)",
            style="bold" if key_selected else "dim",
        )
        self.query_one("#connection-key-label", Static).update(key_label)
        key_input = self.query_one("#connection-key-input", Input)
        key_input.display = self._show_api_key
        key_input.disabled = self._connecting
        self.query_one("#connection-status", Static).update(Text(self._error, style="dim"))
        self.query_one("#connection-hint", Static).update(
            Text.assemble(("Esc", KEY_HINT), (" Back    ", "dim"), ("Enter", KEY_HINT), (" Connect", "dim"))
        )
