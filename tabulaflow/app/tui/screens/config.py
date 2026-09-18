"""Interactive LLM configuration screens."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from tabulaflow.agents.llm import ReasoningLevel
from tabulaflow.app.config import (
    ANTHROPIC_DEFAULT_LLM_CONFIG,
    APP_CONFIG_PATH,
    LLM_OFF,
    MAIN_LLM_MODELS,
    OPENAI_DEFAULT_LLM_CONFIG,
    SUBAGENT_LLM_MODELS,
    LLMRoleConfig,
    ResolvedLLMConfig,
)
from tabulaflow.app.tui.theme import ACCENT_BOLD, KEY_HINT

_CUSTOM_MODEL = "Enter a custom model identifier…"
_REASONING_LEVELS: tuple[ReasoningLevel, ...] = ("minimal", "low", "medium", "high", "xhigh")


class ModelPickerScreen(Screen[str | None]):
    """Full-screen type-to-filter model picker for one agent role."""

    can_focus = True

    DEFAULT_CSS = """
    ModelPickerScreen { background: $background; }
    ModelPickerScreen #model-picker { padding: 1 3; }
    ModelPickerScreen #model-picker-title { height: auto; margin-bottom: 1; }
    ModelPickerScreen #model-options { height: auto; }
    ModelPickerScreen #model-picker-hint { dock: bottom; padding: 0 1; color: #f5f5f5; background: #2a2a2a; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Back", show=False, priority=True),
        Binding("up", "move(-1)", "Previous", show=False, priority=True),
        Binding("down", "move(1)", "Next", show=False, priority=True),
        Binding("enter", "select", "Select", show=False, priority=True),
        Binding("backspace", "erase_filter", "Edit filter", show=False, priority=True),
    ]

    def __init__(self, role: str, current: str) -> None:
        super().__init__()
        self._role = role
        builtins = MAIN_LLM_MODELS if role == "main" else SUBAGENT_LLM_MODELS
        defaults = ANTHROPIC_DEFAULT_LLM_CONFIG if current.startswith("anthropic:") else OPENAI_DEFAULT_LLM_CONFIG
        self._recommended = getattr(defaults, role).model
        ordered = (self._recommended, *(model for model in builtins if model != self._recommended))
        self._models = ordered if current in ordered else (current, *ordered)
        self._visible = self._models
        self._cursor = self._visible.index(current)
        self._filter = ""
        self._editing_custom = False
        self._custom_value = ""
        self._custom_error: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="model-picker"):
            yield Static(id="model-picker-title")
            yield Static(id="model-options")
        yield Static(id="model-picker-hint")

    def on_mount(self) -> None:
        self.focus()
        self._refresh()

    def on_key(self, event: events.Key) -> None:
        if not event.is_printable or event.character is None:
            return
        if self._editing_custom:
            self._custom_value += event.character
            self._custom_error = None
            self._refresh()
        else:
            self._filter += event.character
            self._apply_filter()
        event.stop()
        event.prevent_default()

    def action_move(self, delta: int) -> None:
        if self._editing_custom:
            return
        option_count = len(self._visible) + 1
        self._cursor = max(0, min(option_count - 1, self._cursor + delta))
        self._refresh()

    def action_select(self) -> None:
        if self._editing_custom:
            try:
                model = LLMRoleConfig(model=self._custom_value).model
            except ValueError:
                self._custom_error = "Use the provider:model format."
                self._refresh()
                return
            self.dismiss(model)
            return
        if self._cursor < len(self._visible):
            self.dismiss(self._visible[self._cursor])
            return
        self._editing_custom = True
        self._custom_value = ""
        self._custom_error = None
        self._refresh()

    def action_erase_filter(self) -> None:
        if self._editing_custom:
            if self._custom_value:
                self._custom_value = self._custom_value[:-1]
                self._custom_error = None
                self._refresh()
            return
        if self._filter:
            self._filter = self._filter[:-1]
            self._apply_filter()

    def _apply_filter(self) -> None:
        query = self._filter.casefold()
        self._visible = tuple(model for model in self._models if query in model.casefold())
        self._cursor = 0
        self._refresh()

    def action_cancel(self) -> None:
        if self._editing_custom:
            self._editing_custom = False
            self._custom_error = None
            self._refresh()
            return
        self.dismiss(None)

    def _refresh(self) -> None:
        title_text = "Choose model" if self._role == "main" else "Choose model for subagent"
        title = Text(title_text, style=ACCENT_BOLD)
        if self._filter:
            title.append(" · ", style="dim")
            title.append(f"“{self._filter}”", style="bold")
        self.query_one("#model-picker-title", Static).update(title)

        options = Text()
        for index, model in enumerate(self._visible):
            selected = not self._editing_custom and index == self._cursor
            options.append("❯ " if selected else "  ", style=ACCENT_BOLD if selected else "")
            options.append(model, style="bold" if selected else "")
            if model == self._recommended:
                options.append("  (recommended)", style="dim")
            options.append("\n")

        selected = not self._editing_custom and self._cursor == len(self._visible)
        options.append("❯ " if selected or self._editing_custom else "  ", style=ACCENT_BOLD)
        if self._editing_custom:
            options.append("Custom model", style="bold")
            options.append("\n    ")
            if self._custom_value:
                options.append(self._custom_value, style="bold")
            else:
                options.append("provider:model", style="dim")
            options.append("_", style=ACCENT_BOLD)
            if self._custom_error is not None:
                options.append(f"\n    {self._custom_error}", style="red")
        else:
            options.append(_CUSTOM_MODEL, style="bold" if selected else "")
        self.query_one("#model-options", Static).update(options)

        if self._editing_custom:
            hint = Text.assemble(
                ("Esc", KEY_HINT),
                (" Back · ", "dim"),
                ("Type", KEY_HINT),
                (" Enter identifier · ", "dim"),
                ("Enter", KEY_HINT),
                (" Use", "dim"),
            )
        else:
            hint = Text.assemble(
                ("Esc", KEY_HINT),
                (" Back · ", "dim"),
                ("↑↓", KEY_HINT),
                (" Navigate · ", "dim"),
                ("Type", KEY_HINT),
                (" Filter · ", "dim"),
                ("Enter", KEY_HINT),
                (" Select", "dim"),
            )
        self.query_one("#model-picker-hint", Static).update(hint)


class ConfigScreen(Screen[ResolvedLLMConfig | None]):
    """Full-screen editor for main-agent and subagent model settings."""

    DEFAULT_CSS = """
    ConfigScreen { background: $background; }
    ConfigScreen #config-body { padding: 1 3; }
    ConfigScreen .config-field { height: auto; padding: 0 1; }
    ConfigScreen #config-hint { dock: bottom; padding: 0 1; color: #f5f5f5; background: #2a2a2a; }
    """

    BINDINGS = [
        Binding("escape", "close", "Back", show=False),
        Binding("up", "move(-1)", "Previous", show=False),
        Binding("down", "move(1)", "Next", show=False),
        Binding("left", "change(-1)", "Previous value", show=False),
        Binding("right", "change(1)", "Next value", show=False),
        Binding("enter", "edit", "Select", show=False),
    ]

    def __init__(self, current: ResolvedLLMConfig) -> None:
        super().__init__()
        self._current = current
        self._enabled = current.config is not None
        default = (
            ANTHROPIC_DEFAULT_LLM_CONFIG
            if not os.getenv("OPENAI_API_KEY", "").strip() and os.getenv("ANTHROPIC_API_KEY", "").strip()
            else OPENAI_DEFAULT_LLM_CONFIG
        )
        self._config = (current.config or default).model_copy(deep=True)
        self._initial_enabled = self._enabled
        self._initial_config = self._config.model_copy(deep=True)
        self._cursor = 0
        self._fields = ("enabled", "main-model", "main-reasoning", "subagent-model", "subagent-reasoning")

    @property
    def dirty(self) -> bool:
        return self._enabled != self._initial_enabled or self._config != self._initial_config

    def compose(self) -> ComposeResult:
        config_path = APP_CONFIG_PATH.replace(str(Path.home()), "~", 1)
        with Vertical(id="config-body"):
            yield Static(Text.assemble(("Configuration", ACCENT_BOLD), (f" · saved to {config_path}", "dim")))
            yield Static(id="field-enabled", classes="config-field")
            yield Static(id="field-main-model", classes="config-field")
            yield Static(id="field-main-reasoning", classes="config-field")
            yield Static(id="field-subagent-model", classes="config-field")
            yield Static(id="field-subagent-reasoning", classes="config-field")
        yield Static(id="config-hint")

    def on_mount(self) -> None:
        self._refresh()

    def action_move(self, delta: int) -> None:
        self._cursor = max(0, min(len(self._fields) - 1, self._cursor + delta))
        self._refresh()

    def action_change(self, delta: int) -> None:
        field = self._fields[self._cursor]
        if field == "enabled":
            self._enabled = delta > 0
        elif self._enabled and field.endswith("-reasoning"):
            role_name = field.split("-", 1)[0]
            role = cast(LLMRoleConfig, getattr(self._config, role_name))
            index = _REASONING_LEVELS.index(role.reasoning) if role.reasoning in _REASONING_LEVELS else 2
            role.reasoning = _REASONING_LEVELS[max(0, min(len(_REASONING_LEVELS) - 1, index + delta))]
        self._refresh()

    def action_edit(self) -> None:
        field = self._fields[self._cursor]
        if field == "enabled":
            self._enabled = not self._enabled
            self._refresh()
            return
        if not self._enabled:
            return
        role_name, setting = field.split("-", 1)
        role = cast(LLMRoleConfig, getattr(self._config, role_name))
        if setting == "model":
            self.app.push_screen(
                ModelPickerScreen(role_name, role.model), lambda value: self._set_model(role_name, value)
            )
        else:
            self.action_change(1)

    def _set_model(self, role_name: str, model: str | None) -> None:
        if model is not None:
            getattr(self._config, role_name).model = model
            self._refresh()

    def action_close(self) -> None:
        if not self.dirty:
            self.dismiss(None)
        elif not self._enabled:
            self.dismiss(ResolvedLLMConfig(LLM_OFF, None))
        else:
            config = self._config.model_copy(deep=True)
            self.dismiss(ResolvedLLMConfig(config, config))

    def _refresh(self) -> None:
        values = {
            "enabled": "enabled" if self._enabled else "disabled",
            "main-model": self._config.main.model,
            "main-reasoning": str(self._config.main.reasoning),
            "subagent-model": self._config.subagent.model,
            "subagent-reasoning": str(self._config.subagent.reasoning),
        }
        labels = {
            "enabled": "LLM",
            "main-model": "Model",
            "main-reasoning": "Reasoning",
            "subagent-model": "Subagent model",
            "subagent-reasoning": "Subagent reasoning",
        }
        for index, field in enumerate(self._fields):
            cursor = index == self._cursor
            text = Text("❯ " if cursor else "  ", style=ACCENT_BOLD if cursor else "")
            text.append(f"{labels[field]:<22}", style="bold" if cursor else "")
            if field.endswith("-reasoning"):
                text.append("‹ ", style="dim")
            text.append(
                values[field], style="bold" if cursor else ("" if self._enabled or field == "enabled" else "dim")
            )
            if field.endswith("-reasoning"):
                text.append(" ›", style="dim")
            elif field.endswith("-model"):
                text.append("  ›", style="dim")
            self.query_one(f"#field-{field}", Static).update(text)

        field = self._fields[self._cursor]
        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back · ", style="dim")
        hint.append("↑↓", style=KEY_HINT)
        hint.append(" Navigate", style="dim")
        if field == "enabled" or field.endswith("-reasoning"):
            hint.append(" · ", style="dim")
            hint.append("←→", style=KEY_HINT)
            hint.append(" Change", style="dim")
        elif self._enabled:
            hint.append(" · ", style="dim")
            hint.append("Enter", style=KEY_HINT)
            hint.append(" Select", style="dim")
        self.query_one("#config-hint", Static).update(hint)
