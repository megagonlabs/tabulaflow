"""Input completion candidates and their menu."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.widgets import Static

from tabulaflow.app.theme import ACCENT
from tabulaflow.app.tui.commands import SLASH_COMMANDS, SLASH_COMMAND_DESCRIPTIONS

_CONNECTABLE_EXTENSIONS = frozenset(
    {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson", ".sqlite", ".sqlite3", ".db", ".duckdb"}
)
_VISIBLE_SUGGESTIONS = 8
_MAX_PATH_SUGGESTIONS = 1_000


@dataclass(frozen=True)
class InputSuggestion:
    value: str
    label: str
    description: str = ""


class InputSuggester:
    """Provide slash-command and ``/connect`` path completions."""

    def get_suggestions(self, value: str) -> tuple[InputSuggestion, ...]:
        if value.startswith("/connect "):
            return self._connect_path_suggestions(value)
        if value.startswith("/") and " " not in value:
            return self._slash_command_suggestions(value)
        return ()

    @staticmethod
    def _slash_command_suggestions(value: str) -> tuple[InputSuggestion, ...]:
        return tuple(
            InputSuggestion(
                value=command,
                label=command,
                description=SLASH_COMMAND_DESCRIPTIONS[command],
            )
            for command in SLASH_COMMANDS
            if command.startswith(value) and command != value
        )

    @staticmethod
    def _connect_path_suggestions(value: str) -> tuple[InputSuggestion, ...]:
        raw = value[len("/connect ") :]
        if not raw:
            return ()

        tokens = raw.split()
        partial = tokens[-1] if tokens else raw
        prompt_prefix = value[: len(value) - len(partial)]
        path = Path(partial)
        if partial.endswith("/"):
            parent = path
            name_prefix = ""
        else:
            parent = path.parent
            name_prefix = path.name

        try:
            entries = sorted(parent.iterdir(), key=lambda entry: entry.name.lower())
        except OSError:
            return ()

        files: list[Path] = []
        directories: list[Path] = []
        for entry in entries:
            if not entry.name.startswith(name_prefix) or entry.name.startswith(".") or entry.name == name_prefix:
                continue
            if entry.is_dir():
                directories.append(entry)
            elif entry.suffix.lower() in _CONNECTABLE_EXTENSIONS:
                files.append(entry)

        suggestions = [InputSuggestion(value=f"{prompt_prefix}{entry}", label=str(entry)) for entry in files]
        suggestions.extend(
            InputSuggestion(value=f"{prompt_prefix}{entry}/", label=f"{entry}/") for entry in directories
        )
        return tuple(suggestions[:_MAX_PATH_SUGGESTIONS])


class InputSuggestionMenu(Static):
    """Non-focusable completion list controlled by the prompt editor."""

    can_focus = False

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.suggestions: tuple[InputSuggestion, ...] = ()
        self.selected_index = 0
        self._window_start = 0

    @property
    def selected(self) -> InputSuggestion | None:
        if not self.suggestions:
            return None
        return self.suggestions[self.selected_index]

    def set_suggestions(self, suggestions: tuple[InputSuggestion, ...]) -> None:
        self.suggestions = suggestions
        self.selected_index = 0
        self._window_start = 0
        self.display = bool(suggestions)
        self.refresh()

    def dismiss(self) -> None:
        self.suggestions = ()
        self.selected_index = 0
        self._window_start = 0
        self.display = False
        self.refresh()

    def move_selection(self, offset: int) -> None:
        if not self.suggestions:
            return
        self.selected_index = (self.selected_index + offset) % len(self.suggestions)
        if self.selected_index < self._window_start:
            self._window_start = self.selected_index
        elif self.selected_index >= self._window_start + _VISIBLE_SUGGESTIONS:
            self._window_start = self.selected_index - _VISIBLE_SUGGESTIONS + 1
        self.refresh()

    def render(self) -> Text:
        rendered = Text()
        visible = self.suggestions[self._window_start : self._window_start + _VISIBLE_SUGGESTIONS]
        label_width = min(24, max((len(item.label) for item in visible), default=0))
        for visible_index, suggestion in enumerate(visible):
            index = self._window_start + visible_index
            selected = index == self.selected_index
            style = f"bold {ACCENT}" if selected else ""
            rendered.append(suggestion.label.ljust(label_width), style=style)
            if suggestion.description:
                rendered.append(f"  {suggestion.description}", style=style if selected else "dim")
            if visible_index < len(visible) - 1:
                rendered.append("\n")
        return rendered
