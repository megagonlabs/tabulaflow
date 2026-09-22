"""Chat input, history, paste handling, and completion."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from filelock import FileLock, Timeout as FileLockTimeout
from pydantic_ai.messages import BinaryContent
from rich.highlighter import Highlighter
from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.css.query import NoMatches
from textual.widgets import TextArea
from textual.widgets.text_area import Selection

from tabulaflow.app.theme import CODE_FUNCTION
from tabulaflow.app.tui.clipboard import read_clipboard_image
from tabulaflow.app.tui.widgets.suggestions import InputSuggester, InputSuggestionMenu

if TYPE_CHECKING:
    from tabulaflow.agents.chat import ChatInput
    from tabulaflow.app.tui.app import TabulaflowApp

_MAX_HISTORY_BYTES = 10 * 1024 * 1024
_HISTORY_COMPACTION_RATIO = 0.8
_HISTORY_LOCK_TIMEOUT_SECONDS = 1

logger = logging.getLogger(__name__)

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


class HistoryInput(TextArea):
    """Auto-growing prompt editor with file-backed command history.

    Multi-line pastes (text containing a newline) are stashed in an in-memory
    registry and replaced with a compact ``[Pasted text #N +M lines]`` reference
    so pasted payloads remain compact. Images use highlighted ``[Image #N]``
    references backed only for the active composition. :meth:`build_chat_input`
    expands both forms before submission.
    """

    _MAX_HEIGHT = 5

    class Submitted(Message):
        def __init__(self, input: HistoryInput, value: str) -> None:
            self.input = input
            self.value = value
            super().__init__()

        @property
        def control(self) -> HistoryInput:
            return self.input

    BINDINGS = [
        # ``priority=False`` so these only fire when the input is actually
        # focused. With ``priority=True`` the bindings would claim ``up`` /
        # ``down`` globally, blocking the AgentResultWidget's own arrow-
        # key navigation between result cards.
        Binding("up", "cursor_up_or_history_prev", "Cursor up / previous command", show=False),
        Binding("down", "cursor_down_or_history_next", "Cursor down / next command", show=False),
        Binding("ctrl+d", "confirm_quit", "Quit", show=False, priority=True),
        Binding("tab", "accept_suggestion", "Accept suggestion", show=False),
        Binding("escape", "dismiss_suggestions", "Dismiss suggestions", show=False),
        Binding("ctrl+o", "open_data_explorer", "Open data explorer"),
        # Option/Alt+Arrow word movement. Textual already binds these
        # actions to ``ctrl+left``/``ctrl+right`` (which is what iTerm2 and
        # Terminal.app's "Use Option as Meta key" deliver, via ESC-b/ESC-f).
        # Modern terminals (gnome-terminal, kitty, Ghostty, WezTerm, ...) emit
        # the modifier-3 sequence that Textual parses as ``alt+left``/
        # ``alt+right`` instead, so bind those names to the same actions.
        Binding("alt+left", "cursor_word_left", "Move cursor left a word", show=False),
        Binding("alt+right", "cursor_word_right", "Move cursor right a word", show=False),
        Binding("alt+shift+left", "cursor_word_left(True)", "Select word left", show=False),
        Binding("alt+shift+right", "cursor_word_right(True)", "Select word right", show=False),
    ]

    def action_open_data_explorer(self) -> None:
        """Push the schema browser. Delegates to the app's action."""
        cast("TabulaflowApp", self.app).action_open_data_explorer()

    def __init__(
        self,
        history_path: Path,
        *,
        placeholder: str = "",
        empty_tab_completion: str | None = None,
        id: str | None = None,
    ) -> None:
        self._pasted_contents: dict[int, _PasteRecord] = {}
        self._active_images: dict[int, BinaryContent] = {}
        self._image_counter = 0
        self.highlighter = _ReferenceHighlighter(self._pasted_contents, self._active_images)
        self._suggester = InputSuggester()
        self._dismissed_suggestion_value: str | None = None
        self._empty_tab_completion = empty_tab_completion
        super().__init__(
            placeholder=placeholder,
            id=id,
            soft_wrap=True,
            compact=True,
            highlight_cursor_line=False,
        )
        self.cursor_blink = False
        self._history_path = history_path
        self._history: list[str] = []
        self._history_index: int = -1
        self._saved_input: str = ""
        self._paste_counter: int = 0
        self._load_history()

    @property
    def value(self) -> str:
        return self.text

    @value.setter
    def value(self, value: str) -> None:
        self.load_text(value)

    @property
    def cursor_position(self) -> int:
        return self._location_to_offset(self.cursor_location)

    @cursor_position.setter
    def cursor_position(self, position: int) -> None:
        self.move_cursor(self._offset_to_location(position))

    def get_line(self, line_index: int) -> Text:
        line = super().get_line(line_index)
        self.highlighter.highlight(line)
        return line

    def update_suggestion(self) -> None:
        if hasattr(self, "wrapped_document"):
            self._sync_height()
        value = self.text
        self.suggestion = ""
        menu = self._suggestion_menu()
        if menu is None:
            return
        if not value or not self.selection.is_empty or self.cursor_location != self.document.end:
            menu.dismiss()
            return
        if value == self._dismissed_suggestion_value:
            menu.dismiss()
            return
        self._dismissed_suggestion_value = None
        menu.set_suggestions(self._suggester.get_suggestions(value))

    def _suggestion_menu(self) -> InputSuggestionMenu | None:
        if not self.is_attached:
            return None
        try:
            return self.screen.query_one("#input-suggestions", InputSuggestionMenu)
        except NoMatches:
            return None

    def _on_resize(self) -> None:
        super()._on_resize()
        self._sync_height()

    def _sync_height(self) -> None:
        height = min(self._MAX_HEIGHT, max(1, self.wrapped_document.height))
        if self.size.height != height:
            self.styles.height = height

    def _offset_to_location(self, offset: int) -> tuple[int, int]:
        remaining = max(0, min(offset, len(self.text)))
        for row, line in enumerate(self.document.lines):
            if remaining <= len(line):
                return row, remaining
            remaining -= len(line) + 1
        return self.document.end

    def _location_to_offset(self, location: tuple[int, int]) -> int:
        row, column = location
        return sum(len(line) + 1 for line in self.document.lines[:row]) + column

    def insert_text_at_cursor(self, text: str) -> None:
        result = self.replace(text, *self.selection, maintain_selection_offset=False)
        self.move_cursor(result.end_location)

    def action_submit(self) -> None:
        self.post_message(self.Submitted(self, self.text))

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            menu = self._suggestion_menu()
            if menu is not None and menu.selected is not None:
                self.action_accept_suggestion()
            else:
                self.action_submit()
            return
        await super()._on_key(event)

    def action_cursor_up_or_history_prev(self) -> None:
        menu = self._suggestion_menu()
        if menu is not None and menu.selected is not None:
            menu.move_selection(-1)
            return
        location = self.get_cursor_up_location()
        if location != self.cursor_location:
            self.move_cursor(location)
        else:
            self.action_history_prev()

    def action_cursor_down_or_history_next(self) -> None:
        menu = self._suggestion_menu()
        if menu is not None and menu.selected is not None:
            menu.move_selection(1)
            return
        location = self.get_cursor_down_location()
        if location != self.cursor_location:
            self.move_cursor(location)
        else:
            self.action_history_next()

    def _watch_selection(self, previous: Selection, selection: Selection) -> None:
        previous_offset = self._location_to_offset(previous.end)
        start = self._snap_to_reference_boundary(self._location_to_offset(selection.start), previous_offset)
        end = self._snap_to_reference_boundary(self._location_to_offset(selection.end), previous_offset)
        normalized = Selection(self._offset_to_location(start), self._offset_to_location(end))
        if normalized != selection:
            self.selection = normalized
            return
        super()._watch_selection(previous, selection)

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
        for raw in self._history_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
                display: str = record["display"]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
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

    def _append_history(self, entry: str) -> None:
        """Append one history entry and compact the file when it grows too large."""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        line = (json.dumps(self._build_history_record(entry), ensure_ascii=False) + "\n").encode()
        lock = FileLock(f"{self._history_path}.lock", timeout=_HISTORY_LOCK_TIMEOUT_SECONDS)
        with lock:
            with self._history_path.open("a+b") as file:
                file.seek(0, os.SEEK_END)
                if file.tell() > 0:
                    file.seek(-1, os.SEEK_END)
                    if file.read(1) != b"\n":
                        file.write(b"\n")
                file.write(line)
                file.flush()
            if self._history_path.stat().st_size > _MAX_HISTORY_BYTES:
                self._compact_history()

    def _compact_history(self) -> None:
        lines = self._history_path.read_bytes().splitlines(keepends=True)
        target = int(_MAX_HISTORY_BYTES * _HISTORY_COMPACTION_RATIO)
        retained: list[bytes] = []
        retained_size = 0
        for line in reversed(lines):
            normalized = line if line.endswith(b"\n") else line + b"\n"
            if retained and retained_size + len(normalized) > target:
                break
            retained.append(normalized)
            retained_size += len(normalized)

        temporary = self._history_path.with_name(f".{self._history_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(b"".join(reversed(retained)))
            os.replace(temporary, self._history_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _build_history_record(self, placeholder_text: str) -> dict[str, object]:
        pasted: dict[str, _PasteRecord] = {}
        for m in _PASTE_REFERENCE_PATTERN.finditer(placeholder_text):
            rec = self._pasted_contents.get(int(m.group(1)))
            if rec is not None:
                pasted[str(rec["id"])] = rec
        return {"display": placeholder_text, "pastedContents": pasted}

    def record_submission(self, text: str, *, persist: bool = True) -> None:
        """Append an accepted submission to history and persist it."""
        stripped = text.strip()
        if not stripped:
            return
        self._history.append(stripped)
        self._history_index = -1
        self._saved_input = ""
        if not persist:
            return
        try:
            self._append_history(stripped)
        except (OSError, FileLockTimeout):
            logger.warning("Input was accepted but could not be saved to command history", exc_info=True)

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
        menu = self._suggestion_menu()
        if menu is not None and menu.selected is not None:
            suggestion = menu.selected
            self.value = suggestion.value
            self.cursor_position = len(self.value)
            menu.dismiss()
            return
        if self.text or self._empty_tab_completion is None:
            return
        self.value = self._empty_tab_completion
        self.cursor_position = len(self.value)

    def clear_empty_tab_completion(self) -> None:
        """Disable the optional empty-input Tab completion."""
        self._empty_tab_completion = None

    def action_dismiss_suggestions(self) -> None:
        menu = self._suggestion_menu()
        if menu is None or menu.selected is None:
            cast("TabulaflowApp", self.app).action_toggle_focus()
            return
        self._dismissed_suggestion_value = self.value
        menu.dismiss()

    def action_confirm_quit(self) -> None:
        """Forward Ctrl+D to the app-level quit confirmation when focused."""
        # Input consumes Ctrl+D by default; forward explicitly so the app can
        # apply its double-press quit logic.
        cast("TabulaflowApp", self.app).action_confirm_quit()

    async def _on_paste(self, event: events.Paste) -> None:
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
            result = self.replace(reference, *selection, maintain_selection_offset=False)
            self.move_cursor(result.end_location)
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
                location = self._offset_to_location(match.start())
                self.delete(location, self._offset_to_location(match.end()), maintain_selection_offset=False)
                self.move_cursor(location)
                self._prune_unreferenced_images()
                self.refresh()
                return True
        return False

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
