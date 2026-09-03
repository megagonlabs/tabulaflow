"""Chat input, history, paste handling, and completion."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, TypedDict, cast

from pathlib import Path

from pydantic_ai.messages import BinaryContent
from rich.highlighter import Highlighter
from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.suggester import Suggester
from textual.widgets import Input
from textual.widgets._input import Selection

from tabulaflow.app.theme import CODE_FUNCTION
from tabulaflow.app.tui.commands import SLASH_COMMANDS
from tabulaflow.app.tui.clipboard import read_clipboard_image

if TYPE_CHECKING:
    from tabulaflow.agents.chat import ChatInput
    from tabulaflow.app.tui.app import TabulaflowApp

_CONNECTABLE_EXTENSIONS = frozenset(
    {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson", ".sqlite", ".sqlite3", ".db", ".duckdb"}
)


class TabulaflowSuggester(Suggester):
    """Autocomplete for slash commands and file paths after /connect."""

    def __init__(self) -> None:
        super().__init__(use_cache=False, case_sensitive=True)

    async def get_suggestion(self, value: str) -> str | None:
        if not value:
            return None

        # File path completion after "/connect "
        if value.startswith("/connect "):
            return self._suggest_connect_path(value)

        # Slash command completion
        if value.startswith("/"):
            return self._suggest_slash_command(value)

        return None

    def _suggest_slash_command(self, value: str) -> str | None:
        # Only complete the command portion (first word)
        parts = value.split(" ", 1)
        prefix = parts[0]
        for cmd in SLASH_COMMANDS:
            if cmd.startswith(prefix) and cmd != prefix:
                # Return just the command if user hasn't typed args yet
                if len(parts) == 1:
                    return cmd
                return None
        return None

    def _suggest_connect_path(self, value: str) -> str | None:
        raw = value[len("/connect ") :]
        if not raw:
            return None

        # Split to find the last token (supports multiple file args)
        tokens = raw.split()
        partial = tokens[-1] if tokens else raw
        prefix_part = value[: len(value) - len(partial)]

        p = Path(partial)
        if partial.endswith("/"):
            parent = p
            name_prefix = ""
        else:
            parent = p.parent
            name_prefix = p.name

        try:
            candidates = sorted(parent.iterdir())
        except (OSError, PermissionError):
            return None

        files: list[Path] = []
        dirs: list[Path] = []
        for entry in candidates:
            if not entry.name.startswith(name_prefix) or entry.name.startswith("."):
                continue
            if entry.name == name_prefix:
                continue
            if entry.is_dir():
                dirs.append(entry)
            elif entry.suffix.lower() in _CONNECTABLE_EXTENSIONS:
                files.append(entry)

        # Prioritize files over directories
        for entry in files:
            return f"{prefix_part}{entry}"
        for entry in dirs:
            return f"{prefix_part}{entry}/"
        return None


_MAX_HISTORY_ENTRIES = 500

_PASTE_REFERENCE_PATTERN = re.compile(r"\[Pasted text #(\d+) \+(\d+) lines\]")
_IMAGE_REFERENCE_PATTERN = re.compile(r"\[Image #(\d+)\]")
_REFERENCE_PATTERN = re.compile(r"\[Pasted text #(?P<paste_id>\d+) \+\d+ lines\]|\[Image #(?P<image_id>\d+)\]")


class _PasteRecord(TypedDict):
    """In-memory shape mirrors the on-disk ``pastedContents`` value so save
    and load are trivial mirror operations."""

    id: int
    type: str
    content: str


def _is_active_reference(
    match: re.Match[str],
    pasted_contents: Mapping[int, _PasteRecord],
    images: Mapping[int, BinaryContent],
) -> bool:
    paste_id = match.group("paste_id")
    image_id = match.group("image_id")
    return (paste_id is not None and int(paste_id) in pasted_contents) or (
        image_id is not None and int(image_id) in images
    )


class _ReferenceHighlighter(Highlighter):
    def __init__(
        self,
        pasted_contents: Mapping[int, _PasteRecord],
        images: Mapping[int, BinaryContent],
    ) -> None:
        self._pasted_contents = pasted_contents
        self._images = images

    def highlight(self, text: Text) -> None:
        for match in _REFERENCE_PATTERN.finditer(text.plain):
            if _is_active_reference(match, self._pasted_contents, self._images):
                text.stylize(CODE_FUNCTION, match.start(), match.end())


def _has_newline(text: str) -> bool:
    return "\n" in text or "\r" in text


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class HistoryInput(Input):
    """Input widget with file-backed command history (Up/Down arrows).

    Multi-line pastes (text containing a newline) are stashed in an in-memory
    registry and replaced with a compact ``[Pasted text #N +M lines]`` reference
    so the input bar stays single-line. Images use highlighted ``[Image #N]``
    references backed only for the active composition. :meth:`build_chat_input`
    expands both forms before submission.
    """

    BINDINGS = [
        # ``priority=False`` so these only fire when the input is actually
        # focused. With ``priority=True`` the bindings would claim ``up`` /
        # ``down`` globally, blocking the AgentResultWidget's own arrow-
        # key navigation between result cards.
        Binding("up", "history_prev", "Previous command"),
        Binding("down", "history_next", "Next command"),
        Binding("ctrl+d", "quit_only", "Quit", show=False, priority=True),
        Binding("tab", "accept_suggestion", "Accept suggestion", show=False),
        Binding("ctrl+o", "open_data_explorer", "Open data explorer"),
        # Option/Alt+Arrow word movement. Textual's Input already binds these
        # actions to ``ctrl+left``/``ctrl+right`` (which is what iTerm2 and
        # Terminal.app's "Use Option as Meta key" deliver, via ESC-b/ESC-f).
        # Modern terminals (gnome-terminal, kitty, Ghostty, WezTerm, ...) emit
        # the modifier-3 sequence that Textual parses as ``alt+left``/
        # ``alt+right`` instead, so bind those names to the same actions.
        Binding("alt+left", "cursor_left_word", "Move cursor left a word", show=False),
        Binding("alt+right", "cursor_right_word", "Move cursor right a word", show=False),
        Binding("alt+shift+left", "cursor_left_word(True)", "Select word left", show=False),
        Binding("alt+shift+right", "cursor_right_word(True)", "Select word right", show=False),
    ]

    def action_open_data_explorer(self) -> None:
        """Push the schema browser. Delegates to the app's action."""
        cast("TabulaflowApp", self.app).action_open_data_explorer()

    def __init__(self, history_path: Path, *, placeholder: str = "", id: str | None = None) -> None:
        # ``select_on_focus=False`` so regaining focus (e.g. via the app's
        # typeahead handler after the user types a letter while a result
        # is focused) doesn't replace the in-progress composition with the
        # next keystroke.
        self._pasted_contents: dict[int, _PasteRecord] = {}
        self._active_images: dict[int, BinaryContent] = {}
        self._image_counter = 0
        super().__init__(
            placeholder=placeholder,
            id=id,
            highlighter=_ReferenceHighlighter(self._pasted_contents, self._active_images),
            suggester=TabulaflowSuggester(),
            select_on_focus=False,
        )
        self._history_path = history_path
        self._history: list[str] = []
        self._history_index: int = -1
        self._saved_input: str = ""
        self._paste_counter: int = 0
        self._load_history()

    def _register_paste(self, content: str) -> int:
        """Stash ``content`` under a fresh paste id and return the id."""
        self._paste_counter += 1
        pid = self._paste_counter
        self._pasted_contents[pid] = {"id": pid, "type": "text", "content": content}
        return pid

    def _load_history(self) -> None:
        """Load history from JSONL. Each record is ``{display, pastedContents}``.
        Paste ids from disk are remapped to fresh in-session ids so they don't
        collide with new pastes; the ``display`` string is rewritten to match."""
        if not self._history_path.is_file():
            return
        loaded: list[str] = []
        for raw in self._history_path.read_text(encoding="utf-8").splitlines()[-_MAX_HISTORY_ENTRIES:]:
            if not raw.strip():
                continue
            record = json.loads(raw)
            display: str = record["display"]
            self._image_counter = max(
                self._image_counter,
                max((int(match.group(1)) for match in _IMAGE_REFERENCE_PATTERN.finditer(display)), default=0),
            )
            pasted: dict[str, _PasteRecord] = record.get("pastedContents") or {}

            id_remap = {int(old): self._register_paste(rec["content"]) for old, rec in pasted.items()}

            def remap(m: re.Match[str]) -> str:
                new = id_remap.get(int(m.group(1)))
                return m.group(0) if new is None else f"[Pasted text #{new} +{m.group(2)} lines]"

            loaded.append(_PASTE_REFERENCE_PATTERN.sub(remap, display))
        self._history = loaded

    def _save_history(self) -> None:
        """Persist history as JSONL — one ``{display, pastedContents}`` record
        per line. ``pastedContents`` only includes paste ids actually
        referenced by that entry."""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(self._build_history_record(entry), ensure_ascii=False)
            for entry in self._history[-_MAX_HISTORY_ENTRIES:]
        ]
        self._history_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _build_history_record(self, placeholder_text: str) -> dict[str, object]:
        pasted: dict[str, _PasteRecord] = {}
        for m in _PASTE_REFERENCE_PATTERN.finditer(placeholder_text):
            rec = self._pasted_contents.get(int(m.group(1)))
            if rec is not None:
                pasted[str(rec["id"])] = rec
        return {"display": placeholder_text, "pastedContents": pasted}

    def record_submission(self, text: str) -> None:
        """Append an accepted submission to history and persist it."""
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

    def action_accept_suggestion(self) -> None:
        """Accept the current autocomplete suggestion, if any."""
        if self._suggestion:
            self.value = self._suggestion
            self.cursor_position = len(self.value)

    def action_quit_only(self) -> None:
        """Forward Ctrl+D to the app-level quit-only handler when focused."""
        # Input consumes Ctrl+D by default; forward explicitly so the app can
        # apply its double-press quit logic.
        cast("TabulaflowApp", self.app).action_quit_only()

    def _on_paste(self, event: events.Paste) -> None:
        """Intercept bracketed-paste events with newlines and stash them.

        Textual dispatches ``_on_paste`` for every class in the MRO. For
        single-line pastes we return without doing anything so the parent's
        ``Input._on_paste`` runs normally via that same MRO walk — calling
        ``super()._on_paste`` here would double-insert. For multi-line we
        do the insertion and call ``prevent_default`` to break the MRO walk
        (``stop`` only stops DOM bubbling, not in-widget dispatch).

        Bracketed paste from macOS terminals delivers line breaks as ``\\r``
        rather than ``\\n``, so we treat either as a newline and normalize.
        """
        text = event.text
        if not text or not _has_newline(text):
            return
        self._insert_paste_reference(_normalize_newlines(text))
        event.prevent_default()
        event.stop()

    def action_paste(self) -> None:
        """Paste an image reference or text from the clipboard."""
        try:
            image = read_clipboard_image()
        except (OSError, ValueError) as exc:
            self.notify(str(exc), severity="error")
            return
        if image is not None:
            self._insert_image_reference(image)
            return
        clipboard = getattr(self.app, "clipboard", "") or ""
        if _has_newline(clipboard):
            self._insert_paste_reference(_normalize_newlines(clipboard))
            return
        super().action_paste()

    def _insert_paste_reference(self, text: str) -> None:
        pid = self._register_paste(text)
        line_count = text.count("\n") + 1
        self._insert_reference(f"[Pasted text #{pid} +{line_count} lines]")

    def _insert_image_reference(self, image: BinaryContent) -> None:
        self._image_counter += 1
        image_id = self._image_counter
        self._active_images[image_id] = image
        self._insert_reference(f"[Image #{image_id}]")

    def _insert_reference(self, reference: str) -> None:
        selection = self.selection
        if selection.is_empty:
            self.insert_text_at_cursor(reference)
        else:
            self.replace(reference, *selection)
        self._prune_unreferenced_images()
        self.refresh()

    def action_delete_left(self) -> None:
        if self._delete_adjacent_reference(before_cursor=True):
            return
        super().action_delete_left()
        self._prune_unreferenced_images()

    def action_delete_right(self) -> None:
        if self._delete_adjacent_reference(before_cursor=False):
            return
        super().action_delete_right()
        self._prune_unreferenced_images()

    def _delete_adjacent_reference(self, *, before_cursor: bool) -> bool:
        if not self.selection.is_empty:
            return False
        cursor = self.cursor_position
        for match in _REFERENCE_PATTERN.finditer(self.value):
            if not self._is_active_reference(match):
                continue
            adjacent = match.end() == cursor if before_cursor else match.start() == cursor
            if adjacent:
                self.delete(match.start(), match.end())
                self._prune_unreferenced_images()
                self.refresh()
                return True
        return False

    def validate_selection(self, selection: Selection) -> Selection:
        selection = super().validate_selection(selection)
        previous = self.selection.end
        return Selection(
            self._snap_to_reference_boundary(selection.start, previous),
            self._snap_to_reference_boundary(selection.end, previous),
        )

    def _snap_to_reference_boundary(self, position: int, previous: int) -> int:
        for match in _REFERENCE_PATTERN.finditer(self.value):
            if not self._is_active_reference(match) or not match.start() < position < match.end():
                continue
            if position != previous:
                return match.end() if position > previous else match.start()
            return match.start() if position - match.start() <= match.end() - position else match.end()
        return position

    def build_chat_input(self, text: str) -> ChatInput:
        """Expand visible paste and image references into ordered model input."""
        self._prune_unreferenced_images(text)
        content: list[str | BinaryContent] = []

        def append_text(value: str) -> None:
            if not value:
                return
            if content and isinstance(content[-1], str):
                content[-1] += value
            else:
                content.append(value)

        position = 0
        for match in _REFERENCE_PATTERN.finditer(text):
            append_text(text[position : match.start()])
            if paste_id := match.group("paste_id"):
                record = self._pasted_contents.get(int(paste_id))
                append_text(record["content"] if record is not None else match.group(0))
            elif image_id := match.group("image_id"):
                image = self._active_images.get(int(image_id))
                if image is None:
                    append_text(match.group(0))
                else:
                    append_text(match.group(0))
                    content.append(image)
            position = match.end()
        append_text(text[position:])
        return (
            content
            if any(isinstance(item, BinaryContent) for item in content)
            else "".join(item for item in content if isinstance(item, str))
        )

    def release_submission_images(self, text: str) -> None:
        """Forget images referenced by a completed submission."""
        for match in _IMAGE_REFERENCE_PATTERN.finditer(text):
            self._active_images.pop(int(match.group(1)), None)
        self.refresh()

    def _prune_unreferenced_images(self, text: str | None = None) -> None:
        referenced = {
            int(match.group(1)) for match in _IMAGE_REFERENCE_PATTERN.finditer(self.value if text is None else text)
        }
        for image_id in self._active_images.keys() - referenced:
            del self._active_images[image_id]

    def _is_active_reference(self, match: re.Match[str]) -> bool:
        return _is_active_reference(match, self._pasted_contents, self._active_images)
