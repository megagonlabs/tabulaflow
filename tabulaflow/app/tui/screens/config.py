"""Interactive LLM configuration screen."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from tabulaflow.app.config import (
    APP_CONFIG_PATH,
    LLM_OFF,
    LLM_OFF_LABEL,
    ResolvedLLMSelection,
    load_app_config,
)
from tabulaflow.agents.llm import model_display_name
from tabulaflow.app.theme import (
    ACCENT,
    ACCENT_BOLD,
    KEY_HINT,
)

_CURRENT_CUSTOM_PRESET_LABEL = "Current custom"
_LLM_OPTION_LABEL_WIDTH = 20


class _ConfigLLMRow(Horizontal):
    """LLM option row whose model column retains its indent when wrapped."""

    def __init__(self) -> None:
        super().__init__(classes="config-row")
        self._markers = Static(classes="config-row-markers")
        self._label = Static(classes="config-row-label")
        self._models = Static(classes="config-row-models")

    def compose(self) -> ComposeResult:
        yield self._markers
        yield self._label
        yield self._models

    def update_content(self, markers: Text, label: Text, models: Text) -> None:
        self._markers.update(markers)
        self._label.update(label)
        self._models.update(models)


class ConfigScreen(Screen[ResolvedLLMSelection | None]):
    """Full-screen editor for the active LLM mode."""

    DEFAULT_CSS = """
    ConfigScreen {
        background: $background;
    }

    ConfigScreen #config-body {
        padding: 1 2;
    }

    ConfigScreen .config-row {
        layout: horizontal;
        height: auto;
    }

    ConfigScreen .config-row-markers {
        width: 4;
        height: auto;
    }

    ConfigScreen .config-row-label {
        width: 22;
        height: auto;
        text-wrap: nowrap;
    }

    ConfigScreen .config-row-models {
        width: 1fr;
        height: auto;
    }

    ConfigScreen #config-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Back", show=True),
        Binding("up", "cursor_move(-1)", "Move", show=False),
        Binding("down", "cursor_move(1)", "Move", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    def __init__(self, current: ResolvedLLMSelection) -> None:
        super().__init__()
        app_config = load_app_config()
        presets = list(app_config.llm_presets)
        preset_options = [ResolvedLLMSelection(preset.label, preset) for preset in presets]
        current_custom_preset = current.preset if current.preset is not None and current.preset not in presets else None
        self._current_custom_preset = current_custom_preset
        if current_custom_preset is not None:
            preset_options.insert(
                0,
                ResolvedLLMSelection(
                    current.selection or current_custom_preset.label,
                    current_custom_preset,
                ),
            )
        self._options = [
            ResolvedLLMSelection(LLM_OFF, None),
            *preset_options,
        ]
        self._option_rows = [_ConfigLLMRow() for _ in self._options]
        self._active_index = next(
            (i for i, option in enumerate(self._options) if option.preset == current.preset),
            0,
        )
        self._selected_index = self._active_index
        self._cursor = self._active_index
        self._current = current
        self._selection_confirmed = False

    def compose(self) -> ComposeResult:
        config_path = APP_CONFIG_PATH.replace(str(Path.home()), "~", 1)
        title = Text()
        title.append("Config", style=ACCENT_BOLD)
        title.append(f" · saved to {config_path}", style="dim")
        llm_title = Text("LLM", style="bold")
        llm_title.append(" (main → subagent)", style="dim")
        with Vertical(id="config-body"):
            yield Static(title)
            yield Static("")
            if self._option_rows:
                yield Static(llm_title)
                yield from self._option_rows
        yield Static(self._hint_text(), id="config-hint")

    def on_mount(self) -> None:
        self._refresh()

    def _option_row_parts(self, i: int) -> tuple[Text, Text, Text]:
        option = self._options[i]
        preset = option.preset
        selected = self._cursor == i
        active = self._selected_index == i
        markers = Text()
        markers.append("❯ " if selected else "  ", style=ACCENT_BOLD)
        markers.append("● " if active else "  ", style=ACCENT)
        if active:
            label_style = ACCENT_BOLD if selected else ACCENT
        else:
            label_style = "bold" if selected else ""
        if preset is None:
            option_label = LLM_OFF_LABEL
        elif preset == self._current_custom_preset:
            option_label = _CURRENT_CUSTOM_PRESET_LABEL
        else:
            option_label = preset.label
        label = Text(option_label, style=label_style)
        label.truncate(_LLM_OPTION_LABEL_WIDTH, overflow="ellipsis", pad=True)
        label.append("  ")
        if option.selection == LLM_OFF:
            models = Text("Connect and browse data", style="dim")
        else:
            assert preset is not None
            models = Text(
                f"{model_display_name(preset.main.model, preset.main.reasoning_effort)}"
                f" → {model_display_name(preset.subagent.model, preset.subagent.reasoning_effort)}",
                style="dim",
            )
        return markers, label, models

    def _hint_text(self) -> Text:
        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back", style="dim")
        return hint

    def _refresh(self) -> None:
        for i, row in enumerate(self._option_rows):
            row.update_content(*self._option_row_parts(i))

    def action_cursor_move(self, delta: int) -> None:
        self._cursor = max(0, min(len(self._options) - 1, self._cursor + delta))
        self._refresh()

    def action_select(self) -> None:
        self._select_option(self._cursor)

    def _select_option(self, i: int) -> None:
        self._selected_index = i
        self._selection_confirmed = True
        self._refresh()

    def action_close(self) -> None:
        if not self._selection_confirmed:
            self.dismiss(None)
            return
        selection = self._options[self._selected_index]
        if self._current.selection is not None and selection.selection == self._current.selection:
            self.dismiss(None)
            return
        self.dismiss(selection)
