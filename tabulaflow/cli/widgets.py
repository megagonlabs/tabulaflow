"""Textual widgets for the tabulaflow TUI."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, TypedDict

from rich.console import Group
from rich.spinner import Spinner
from rich.text import Text
from pathlib import Path

from textual import events
from textual.binding import Binding
from textual.reactive import reactive
from textual.suggester import Suggester
from textual.timer import Timer
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Input, Static, TextArea

from tabulaflow.cli.display import DATA_PREVIEW_MAX_ROWS
from tabulaflow.cli.theme import ACCENT, ACCENT_DIM, DRACULA_TRANSPARENT, KEY_HINT, KEY_HINT_DIM


def _normalize_json_like(value: object) -> object:
    """Coerce ``ndarray``/``dict``/``list`` cells into a JSON-ready structure.

    Converts numpy ndarrays to lists and recursively json.loads any string leaf
    that parses as a dict or list — so HF-style JSON-array columns
    (``ndarray([str, str, ...])``) render as structured JSON instead of
    backslash-escaped Python list reprs.
    """
    import numpy as np

    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, dict):
        return {k: _normalize_json_like(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_json_like(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
        if isinstance(parsed, (dict, list)):
            return _normalize_json_like(parsed)
        return value
    return value


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any

    import pandas as pd
    from rich.console import RenderableType

    from tabulaflow.cli.agent import ChatResult
    from tabulaflow.cli.display import RecordGroup, ViewItem
    from tabulaflow.schema import Usage


# ---------------------------------------------------------------------------
# Autocomplete suggester
# ---------------------------------------------------------------------------

_SLASH_COMMANDS = sorted(
    ["/help", "/exit", "/clear", "/connect", "/disconnect", "/databases", "/db", "/schema", "/model"]
)

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
        for cmd in _SLASH_COMMANDS:
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


# ---------------------------------------------------------------------------
# Input with persistent history
# ---------------------------------------------------------------------------

_MAX_HISTORY_ENTRIES = 500

_PASTE_TOKEN_PATTERN = re.compile(r"\[Pasted text #(\d+) \+(\d+) lines\]")


class _PasteRecord(TypedDict):
    """In-memory shape mirrors the on-disk ``pastedContents`` value so save
    and load are trivial mirror operations."""

    id: int  # redundant with the dict key, kept to match Claude Code's on-disk format
    type: str  # always "text" today; extension point for "image" / "file" without a format break
    content: str


def _has_newline(text: str) -> bool:
    return "\n" in text or "\r" in text


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class HistoryInput(Input):
    """Input widget with file-backed command history (Up/Down arrows).

    Multi-line pastes (text containing a newline) are stashed in an in-memory
    registry and replaced with a compact ``[Pasted text #N +M lines]`` token
    so the input bar stays single-line. Submitted text is expanded back to
    the original via :meth:`expand_paste_tokens` before being handed to the
    agent or slash-command handler.
    """

    BINDINGS = [
        # ``priority=False`` so these only fire when the input is actually
        # focused. With ``priority=True`` the bindings would claim ``up`` /
        # ``down`` globally, blocking the AgentResultWidget's own arrow-
        # key navigation between records.
        Binding("up", "history_prev", "Previous command"),
        Binding("down", "history_next", "Next command"),
        Binding("ctrl+d", "quit_only", "Quit", show=False, priority=True),
        Binding("tab", "accept_suggestion", "Accept suggestion", show=False),
        Binding("ctrl+o", "open_data_explorer", "Open data explorer"),
    ]

    def action_open_data_explorer(self) -> None:
        """Push the schema browser. Delegates to the app's action."""
        self.app.action_open_data_explorer()  # type: ignore[attr-defined]

    def __init__(self, history_path: Path, **kwargs: object) -> None:
        # ``select_on_focus=False`` so regaining focus (e.g. via the app's
        # typeahead handler after the user types a letter while a result
        # is focused) doesn't replace the in-progress composition with the
        # next keystroke.
        super().__init__(suggester=TabulaflowSuggester(), select_on_focus=False, **kwargs)  # type: ignore[arg-type]
        self._history_path = history_path
        self._history: list[str] = []
        self._history_index: int = -1
        self._saved_input: str = ""
        self._pasted_contents: dict[int, _PasteRecord] = {}
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
            pasted: dict[str, _PasteRecord] = record.get("pastedContents") or {}

            id_remap = {int(old): self._register_paste(rec["content"]) for old, rec in pasted.items()}

            def remap(m: re.Match[str]) -> str:
                new = id_remap.get(int(m.group(1)))
                return m.group(0) if new is None else f"[Pasted text #{new} +{m.group(2)} lines]"

            loaded.append(_PASTE_TOKEN_PATTERN.sub(remap, display))
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
        for m in _PASTE_TOKEN_PATTERN.finditer(placeholder_text):
            rec = self._pasted_contents.get(int(m.group(1)))
            if rec is not None:
                pasted[str(rec["id"])] = rec
        return {"display": placeholder_text, "pastedContents": pasted}

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Append the submitted text (placeholder form) to history. The
        save step bundles each entry with its referenced paste contents."""
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

    def action_accept_suggestion(self) -> None:
        """Accept the current autocomplete suggestion, if any."""
        if self._suggestion:
            self.value = self._suggestion
            self.cursor_position = len(self.value)

    def action_quit_only(self) -> None:
        """Forward Ctrl+D to the app-level quit-only handler when focused."""
        # Input consumes Ctrl+D by default; forward explicitly so the app can
        # apply its double-press quit logic.
        self.app.action_quit_only()  # type: ignore[attr-defined]

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
        self._insert_paste_token(_normalize_newlines(text))
        event.prevent_default()
        event.stop()

    def action_paste(self) -> None:
        """Override Ctrl+V so pastes from Textual's clipboard route through
        the same multi-line stash logic as terminal bracketed paste."""
        clipboard = getattr(self.app, "clipboard", "") or ""
        if _has_newline(clipboard):
            self._insert_paste_token(_normalize_newlines(clipboard))
            return
        super().action_paste()

    def _insert_paste_token(self, text: str) -> None:
        pid = self._register_paste(text)
        line_count = text.count("\n") + 1
        token = f"[Pasted text #{pid} +{line_count} lines]"
        selection = self.selection
        if selection.is_empty:
            self.insert_text_at_cursor(token)
        else:
            self.replace(token, *selection)

    def expand_paste_tokens(self, text: str) -> str:
        """Replace every ``[Pasted text #N +M lines]`` token with the original
        pasted text. Unknown indices are left untouched so users can still
        type the literal token if they really mean to."""
        if not self._pasted_contents:
            return text

        def repl(m: re.Match[str]) -> str:
            rec = self._pasted_contents.get(int(m.group(1)))
            return m.group(0) if rec is None else rec["content"]

        return _PASTE_TOKEN_PATTERN.sub(repl, text)


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
        from tabulaflow.cli.display import build_banner

        super().__init__(build_banner(model=model))


class UserMessage(Static):
    """Displays a user input message."""

    DEFAULT_CSS = f"""
    UserMessage {{
        margin: 1 0 1 0;
        padding: 0 1;
        border-left: heavy {ACCENT};
    }}
    """

    def __init__(self, text: str) -> None:
        super().__init__(Text(text))


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
        self._label = label
        self._spinner = Spinner("dots", text=Text(label, style="dim"), style="dim")

    def update_label(self, label: str) -> None:
        self._label = label
        self._spinner.text = Text(label, style="dim")

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
        self._steps: list[tuple[str, str, str, str]] = []  # (status, tool_call_id, name, label)
        self._streaming_text = ""
        self._raw_text = ""
        self._separator_seen = False
        self._status_text: str | None = "Thinking..."
        # Persistent spinner instances so animation state survives across renders.
        self._status_spinner = Spinner("dots", text=Text("Thinking...", style="dim"), style="dim")
        # Per-tool-call spinners so parallel running steps don't share a single
        # mutable spinner object (which would make every row display the same label).
        self._tool_spinners: dict[str, Spinner] = {}
        self._tool_progress: tuple[int, int, str | None] | None = None
        self._frozen = False
        self._timer: Timer | None = None
        self._usage: Usage | None = None
        self._interrupted: bool = False

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 12, self.refresh)

    def render(self) -> RenderableType:
        parts: list[RenderableType] = []

        has_running = False
        for status, tool_call_id, _name, label in self._steps:
            if status == "running":
                has_running = True
                if self._frozen:
                    line = Text()
                    line.append("⊘ ", style="dim")
                    line.append(label, style="dim")
                    parts.append(line)
                else:
                    spinner = self._tool_spinners.get(tool_call_id)
                    if spinner is None:
                        spinner = Spinner("dots", style="dim")
                        self._tool_spinners[tool_call_id] = spinner
                    spinner.text = Text(label, style="dim")
                    parts.append(spinner)
            else:
                line = Text()
                line.append("→ ", style="dim")
                line.append(label, style="dim")
                parts.append(line)

        if self._status_text and not has_running:
            if self._frozen:
                parts.append(Text(self._status_text, style="dim"))
            else:
                self._status_spinner.text = Text(self._status_text, style="dim")
                parts.append(self._status_spinner)

        if self._streaming_text:
            if self._steps:
                parts.append(Text())
            parts.append(Text(self._streaming_text))

        return Group(*parts) if parts else Text()

    # ProgressSink interface

    def start(self) -> None:
        pass

    def finish(self) -> None:
        self._status_text = None
        self._frozen = True
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._refresh(layout=True)

    def tool_start(self, tool_call_id: str, name: str, args_summary: str) -> None:
        if self._status_text and self._status_text != "Thinking...":
            self._steps.append(("done", "", "__status__", self._status_text))
        label = f"{name}({args_summary})" if args_summary else name
        self._steps.append(("running", tool_call_id, name, label))
        self._streaming_text = ""
        self._status_text = None
        self._refresh(layout=True, scroll=True)

    def tool_progress(self, completed: int, total: int, stage: str | None = None) -> None:
        """Update the running tool step with a (completed/total) counter.

        When ``stage`` is provided, it's prepended to the counter so the user can
        tell which sub-phase is ticking (e.g. ``resolve: 12/88``).
        """
        self._tool_progress = (completed, total, stage)
        suffix = f"{stage}: {completed}/{total}" if stage else f"{completed}/{total}"
        for i in range(len(self._steps) - 1, -1, -1):
            if self._steps[i][0] == "running":
                base_label = self._steps[i][3].split(" → ")[0]
                self._steps[i] = (
                    "running",
                    self._steps[i][1],
                    self._steps[i][2],
                    f"{base_label} → {suffix}",
                )
                break
        self._refresh(layout=True, scroll=True)

    def tool_end(self, tool_call_id: str, name: str, result_summary: str) -> None:
        for i in range(len(self._steps) - 1, -1, -1):
            step = self._steps[i]
            if step[0] == "running" and step[1] == tool_call_id:
                label = step[3]
                if self._tool_progress is not None:
                    base_label = label.split(" → ")[0]
                    total = self._tool_progress[1]
                    last_stage = self._tool_progress[2]
                    suffix = f"{last_stage}: {total}/{total}" if last_stage else f"{total}/{total}"
                    self._steps[i] = ("done", step[1], step[2], f"{base_label} → {suffix}")
                else:
                    self._steps[i] = ("done", step[1], step[2], f"{label} → {result_summary}")
                break
        self._tool_spinners.pop(tool_call_id, None)
        self._tool_progress = None
        self._status_text = "Thinking..."
        self._refresh(layout=True, scroll=True)

    def text_delta(self, delta: str) -> None:
        self._raw_text += delta
        # Only display text after the --- separator
        if self._separator_seen:
            self._streaming_text += delta
        elif "---" in self._raw_text:
            self._separator_seen = True
            self._streaming_text = self._raw_text.split("---", 1)[1].lstrip("\n")
        else:
            return
        self._status_text = None
        self._refresh(layout=True, scroll=True)

    def set_status(self, text: str) -> None:
        self._status_text = text
        self._refresh()

    def usage_update(self, usage: Usage) -> None:
        self._usage = usage
        self._refresh()

    def freeze_as_interrupted(self) -> None:
        self._interrupted = True
        self._status_text = None
        self._frozen = True
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        # If we never produced any content, collapse out of the layout so the
        # following "Interrupted" line sits flush against the user prompt.
        if not self._steps and not self._streaming_text:
            self.display = False
        self._refresh(layout=True)

    def _refresh(self, *, layout: bool = False, scroll: bool = False) -> None:
        try:
            self.refresh(layout=layout)
            if scroll:
                self.app.query_one("#chat-log").scroll_end(animate=False)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Browser-open helpers (used by Data and Cell browsers)
# ---------------------------------------------------------------------------


def _open_path_in_browser(path: Path, *, status: "Callable[[Text], None]") -> bool:
    """Open ``path`` in the system browser, reporting via ``status``.

    ``webbrowser_open.open`` returns None and raises on failure; we use
    absence of exception (combined with a default-browser probe for the
    headless case) as the success signal.
    """
    import webbrowser_open

    try:
        webbrowser_open.open(path.absolute().as_uri())
        opened = webbrowser_open.get_default_browser() is not None
    except Exception:
        opened = False
    if opened:
        status(Text(f"opened in browser: {path}", style="dim"))
    else:
        status(Text(f"no browser, saved to {path}", style="dim"))
    return opened


def open_cell_in_browser(value: object, app: object, *, status: "Callable[[Text], None]") -> "Path | None":
    """Serialize ``value`` to the dumps dir and open it in the browser.

    Returns the written path on success, or ``None`` if no dumps dir is
    configured or the write failed.
    """
    from tabulaflow.cli.dump import write_cell_dump

    try:
        dumps_dir: Path = app._runtime_paths.dumps_dir  # type: ignore[attr-defined]
    except AttributeError:
        status(Text("save failed: no cell dumps dir", style="red"))
        return None
    try:
        path = write_cell_dump(value, dumps_dir)
    except OSError as exc:
        status(Text(f"write failed: {exc}", style="red"))
        return None
    except Exception as exc:
        status(Text(f"serialize failed: {exc}", style="red"))
        return None
    _open_path_in_browser(path, status=status)
    return path


def open_table_in_browser(
    df: "pd.DataFrame",
    title: str,
    app: object,
    *,
    status: "Callable[[Text], None]",
) -> "Path | None":
    """Render ``df`` as inline-media HTML in the dumps dir and open it.

    Returns the written HTML path on success, or ``None`` on failure.
    """
    import secrets

    from tabulaflow.cli.dump import render_table_html

    try:
        dumps_dir: Path = app._runtime_paths.dumps_dir  # type: ignore[attr-defined]
    except AttributeError:
        status(Text("save failed: no cell dumps dir", style="red"))
        return None
    html_path = dumps_dir / f"T_{secrets.token_hex(3)}.html"
    try:
        render_table_html(df, html_path, title=title)
    except OSError as exc:
        status(Text(f"write failed: {exc}", style="red"))
        return None
    except Exception as exc:
        status(Text(f"render failed: {exc}", style="red"))
        return None
    _open_path_in_browser(html_path, status=status)
    return html_path


# ---------------------------------------------------------------------------
# Data browser screen
# ---------------------------------------------------------------------------


class DataBrowserScreen(Screen[None]):
    """Full-screen browser for inspecting query result rows."""

    DEFAULT_CSS = """
    DataBrowserScreen {
        background: $background;
    }

    DataBrowserScreen .data-browser-grid {
        height: 1fr;
        margin: 0 1;
        border: solid #3EB489;
        background: $background;
        color: $text;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    DataBrowserScreen .data-browser-grid > .datatable--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid:focus {
        border: solid #3EB489;
        outline: none;
        background-tint: transparent 0%;
    }

    DataBrowserScreen .data-browser-grid > .datatable--fixed-cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid:focus > .datatable--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid:focus > .datatable--fixed-cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid > .datatable--fixed {
        background: transparent;
        color: #888888;
    }

    DataBrowserScreen .data-browser-grid > .datatable--header {
        background: transparent;
        color: #3EB489;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid > .datatable--header-hover {
        background: transparent;
        color: #3EB489;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid > .datatable--header-cursor {
        background: transparent;
        color: #3EB489;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }

    DataBrowserScreen .data-browser-status {
        padding: 0 1;
        color: #f5f5f5;
    }

    DataBrowserScreen .data-browser-gap {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("enter", "open_cell", "Inspect cell", priority=True),
        Binding("[", "prev_page", "Prev page", show=True),
        Binding("]", "next_page", "Next page", show=True),
        Binding("b", "open_table_in_browser", "Open table in browser", show=True, priority=True),
    ]

    def __init__(self, *, title: str, df: "pd.DataFrame", page_size: int = 50) -> None:
        super().__init__()
        self._title = title
        self._df = df
        self._page_size = max(1, page_size)
        self._page_index = 0
        self._sorted_column: str | None = None
        self._sort_reverse = False
        self._table: DataTable[Text] = DataTable(
            zebra_stripes=True,
            classes="data-browser-grid",
            header_height=2,
            show_cursor=True,
            cursor_type="cell",
            cursor_background_priority="css",
            cursor_foreground_priority="css",
            fixed_columns=1,
        )
        self._status = Static(classes="data-browser-status")
        self._gap = Static(classes="data-browser-gap")
        self._hint = Static(classes="data-browser-hint")

    def compose(self) -> ComposeResult:
        yield self._table
        yield self._status
        yield self._gap
        yield self._hint

    def on_mount(self) -> None:
        self._table.focus()
        self._render_page()

    def action_close_browser(self) -> None:
        self.dismiss()

    async def action_open_cell(self) -> None:
        """Open cell value browser for the currently highlighted cell.

        Yields one event-loop tick after updating the status so Textual
        gets to paint ``Loading cell...`` before we run the (CPU-bound,
        GIL-holding) ``_format_value`` synchronously.
        """
        import asyncio

        row_idx = self._table.cursor_coordinate.row
        col_idx = self._table.cursor_coordinate.column
        # Column 0 is the row-number column; skip it.
        if col_idx <= 0:
            return
        df_col = col_idx - 1
        if df_col >= len(self._df.columns):
            return
        start = self._page_index * self._page_size
        df_row = start + row_idx
        if df_row >= len(self._df):
            return
        col_name = str(self._df.columns[df_col])
        raw_value = self._df.iloc[df_row, df_col]
        row_number = df_row + 1
        dtype_str = self._describe_dtype(self._df[col_name])

        self._status.update(Text("Loading cell...", style="dim"))
        # Wait until Textual has actually painted the new status before we
        # block the main thread with _format_value (CPU-bound, holds GIL).
        painted: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self.call_after_refresh(lambda: painted.done() or painted.set_result(None))
        await painted
        try:
            display_text, language = CellBrowserScreen._format_value(raw_value)
        finally:
            self._update_status()
        self.app.push_screen(
            CellBrowserScreen(
                column_name=col_name,
                row_number=row_number,
                value=raw_value,
                dtype_str=dtype_str,
                display_text=display_text,
                language=language,
            )
        )

    def action_next_page(self) -> None:
        if self._page_index < self._max_page_index:
            self._page_index += 1
        else:
            self._page_index = 0
        self._render_page()

    def action_prev_page(self) -> None:
        if self._page_index > 0:
            self._page_index -= 1
        else:
            self._page_index = self._max_page_index
        self._render_page()

    async def action_open_table_in_browser(self) -> None:
        """Open the current DataFrame as HTML in the system browser.

        Shows ``Opening...`` while the (blocking) render runs, paints
        before the block, then the helper overwrites the status with the
        final result (``opened in browser: <path>`` or ``no browser, saved
        to: <path>``).
        """
        import asyncio

        self._set_status_message(Text("Opening...", style="dim"))
        painted: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self.call_after_refresh(lambda: painted.done() or painted.set_result(None))
        await painted
        open_table_in_browser(self._df, self._title, self.app, status=self._set_status_message)

    def _set_status_message(self, message: "Text") -> None:
        """Display a transient status message from a browser-open helper."""
        self._status.update(message)

    @property
    def _num_rows(self) -> int:
        return len(self._df)

    @property
    def _max_page_index(self) -> int:
        if self._num_rows == 0:
            return 0
        return (self._num_rows - 1) // self._page_size

    def _render_page(self) -> None:
        start = self._page_index * self._page_size
        end = min(start + self._page_size, self._num_rows)
        page_df = self._df.iloc[start:end]

        header_labels = ["#"]
        for col in page_df.columns:
            label = str(col)
            if self._sorted_column == label:
                marker = "▼" if self._sort_reverse else "▲"
                label = f"{label} {marker}"
            header_labels.append(label)
        # Textual's DataTable.clear() always resets scroll_x; save and restore.
        scroll_x = self._table.scroll_x
        self._table.clear(columns=True)
        self._table.add_columns(*header_labels)

        for local_idx, row in enumerate(page_df.itertuples(index=False, name=None), start=1):
            row_number = start + local_idx
            row_label = Text(f"{row_number:,}", justify="right")
            cells = [row_label] + [self._format_cell(v) for v in row]
            self._table.add_row(*cells)

        self._table.scroll_to(x=scroll_x, y=0, animate=False)
        self._update_status()
        self._update_hint()

    def _update_status(self) -> None:
        total_pages = self._max_page_index + 1
        start = self._page_index * self._page_size
        end = min(start + self._page_size, self._num_rows)
        shown_range = "0-0" if self._num_rows == 0 else f"{start + 1}-{end}"

        parts = [
            self._title,
            f"{self._num_rows:,} rows x {len(self._df.columns)} cols",
            f"Rows {shown_range} of {self._num_rows:,}",
            f"Page {self._page_index + 1}/{total_pages}",
        ]

        col_index = self._table.cursor_coordinate.column - 1
        if 0 <= col_index < len(self._df.columns):
            col_name = str(self._df.columns[col_index])
            col_dtype = self._describe_dtype(self._df[col_name])
            parts.append(f"{col_name} ({col_dtype})")

        self._status.update(Text("  |  ".join(parts), style="dim"))

    def _update_hint(self) -> None:
        hint_fg = "dim"
        hint_segments: list[tuple[str, str]] = [
            ("Esc", KEY_HINT),
            (" Back    ", hint_fg),
            ("↵", KEY_HINT),
            (" Inspect cell    ", hint_fg),
            ("[", KEY_HINT),
            ("/", hint_fg),
            ("]", KEY_HINT),
            (" Prev/Next page    ", hint_fg),
            ("B", KEY_HINT),
            (" Open table in browser", hint_fg),
        ]
        hint = Text()
        for text, style in hint_segments:
            hint.append(text, style=style)
        self._hint.update(hint)

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """Update status bar with selected column dtype."""
        if event.data_table is self._table:
            self._update_status()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Suppress default Enter behavior on cells."""
        event.stop()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Sort when user clicks a header cell."""
        if event.data_table is not self._table:
            return
        self._sort_by_column_index(event.column_index)
        event.stop()

    def _sort_by_column_index(self, column_index: int) -> None:
        """Sort by a displayed column index; index 0 is row number and ignored."""
        if column_index <= 0:
            return
        col_pos = column_index - 1
        if col_pos < 0 or col_pos >= len(self._df.columns):
            return
        column = str(self._df.columns[col_pos])
        if self._sorted_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sorted_column = column
            self._sort_reverse = False
        self._df = self._df.sort_values(
            by=column,
            ascending=not self._sort_reverse,
            kind="mergesort",
            na_position="last",
        )
        self._page_index = 0
        self._render_page()

    _MAX_CELL_LEN = 80

    @staticmethod
    def _describe_dtype(series: "pd.Series") -> str:
        """Return a human-readable dtype label, resolving 'object' to the actual Python type."""
        dtype_str = str(series.dtype)
        if dtype_str != "object":
            return dtype_str
        sample = series.dropna().head(20)
        if sample.empty:
            return "object"
        types = {type(v).__name__ for v in sample}
        if len(types) == 1:
            return types.pop()
        return "mixed"

    @staticmethod
    def _format_cell(value: object) -> Text:
        import numbers

        import numpy as np
        import pandas as pd_

        try:
            if value is None or pd_.isna(value):
                return Text("NULL", style="dim italic")
        except (TypeError, ValueError):
            pass

        if isinstance(value, bool):
            return Text("✔" if value else "✘", style=ACCENT if value else "dim")

        if isinstance(value, numbers.Integral):
            return Text(f"{value:,}", justify="right")

        if isinstance(value, numbers.Real):
            return Text(f"{value:,}", justify="right")

        # Short-circuit binary cells before ``str(value)`` allocates the
        # full escaped-hex repr. For a single 1 MB BLOB ``str()`` produces
        # ~5 MB of escaped chars, which then gets truncated to 80 chars —
        # the work is wasted and stalls page renders on tables with
        # image / audio / video columns.
        if isinstance(value, (bytes, bytearray, memoryview)):
            return Text(f"<binary: {len(value):,} bytes>", style="dim italic")
        # HuggingFace Image/Audio struct: ``{"bytes": <blob>, "path": ...}``
        if isinstance(value, dict):
            inner = value.get("bytes")
            if isinstance(inner, (bytes, bytearray, memoryview)):
                return Text(f"<binary: {len(inner):,} bytes>", style="dim italic")

        if isinstance(value, (np.ndarray, list, dict)):
            try:
                s = json.dumps(_normalize_json_like(value), ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                s = str(value)
        else:
            s = str(value)
        # Truncate before the replace chain so the per-cell cost stays
        # O(_MAX_CELL_LEN) instead of O(full-string-length). For huge text
        # cells (megabytes of content) the replace passes and downstream
        # Rich rendering were dominating page-render time.
        truncated = len(s) > DataBrowserScreen._MAX_CELL_LEN
        if truncated:
            s = s[: DataBrowserScreen._MAX_CELL_LEN]
        # Normalize whitespace to single spaces — collapses newlines
        # (which DataTable otherwise renders as hard line breaks,
        # expanding the row), tabs, and runs of spaces. Full multi-line
        # content stays available via Enter to inspect.
        s = " ".join(s.split())
        # Match the dim-italic styling of the ``NULL`` and ``<binary: N
        # bytes>`` placeholders — ``<binary: skipped>`` plays the same
        # role (a placeholder for stripped BLOB data, produced by the HF
        # loader's ``blob_strip=True``).
        if s == "<binary: skipped>":
            return Text(s, style="dim italic")
        if truncated:
            t = Text(s[: DataBrowserScreen._MAX_CELL_LEN - 3])
            t.append("...", style="dim")
            return t
        return Text(s)


# ---------------------------------------------------------------------------
# Cell value browser screen
# ---------------------------------------------------------------------------


class CellBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a single cell value."""

    DEFAULT_CSS = """
    CellBrowserScreen {
        background: $background;
    }

    CellBrowserScreen TextArea {
        height: 1fr;
        margin: 0 1;
        border: solid white;
        background: $background;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    CellBrowserScreen TextArea:focus {
        border: solid white;
        outline: none;
    }

    CellBrowserScreen .cell-browser-status {
        padding: 0 1;
        color: #f5f5f5;
    }

    CellBrowserScreen .cell-browser-gap {
        height: 1;
    }

    CellBrowserScreen .cell-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("b", "open_in_browser", "Open cell in browser", show=True, priority=True),
    ]

    # Skip syntax highlighting above this many rendered chars — Pygments'
    # upfront pass blocks the UI for several seconds on multi-MB JSON.
    _MAX_HIGHLIGHT_CHARS = 200_000
    # Disable soft_wrap when any line exceeds this length — wrap recompute
    # on a single very long line dominates scroll/cursor cost in TextArea.
    _MAX_SOFT_WRAP_LINE = 500
    # Soft cap on the rendered display text. Beyond this, append a footer
    # pointing the user at `b` for full-fidelity content via the browser
    # (which goes through ``dump.serialize_cell``, bypassing this cap).
    _MAX_DISPLAY_CHARS = 1_000_000

    def __init__(
        self,
        *,
        column_name: str,
        row_number: int,
        value: object,
        dtype_str: str,
        display_text: str | None = None,
        language: str | None = None,
    ) -> None:
        super().__init__()
        self._column_name = column_name
        self._row_number = row_number
        self._raw_value = value
        self._dtype_str = dtype_str
        # Cache the path written by ``action_open_in_browser`` so repeated
        # presses of `b` reuse the same file (and may reuse the same
        # browser tab) instead of writing a new dump every time.
        self._dumped_path: Path | None = None
        if display_text is None:
            self._display_text, self._language = self._format_value(value)
        else:
            self._display_text, self._language = display_text, language

    _SQL_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|EXPLAIN)\b", re.IGNORECASE)
    _PY_RE = re.compile(r"^\s*(def |class |import |from |if __name__)")

    _MAX_JSON_LEAF = 1000

    @staticmethod
    def _truncate_json_leaves(obj: object, max_len: int) -> object:
        """Recursively truncate long string/bytes leaves in a JSON-like structure."""
        if isinstance(obj, dict):
            return {k: CellBrowserScreen._truncate_json_leaves(v, max_len) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CellBrowserScreen._truncate_json_leaves(v, max_len) for v in obj]
        if isinstance(obj, (bytes, bytearray)):
            if len(obj) > max_len:
                return f"<binary: {len(obj):,} bytes>"
            return obj.hex(" ")
        if isinstance(obj, str) and len(obj) > max_len:
            return obj[:max_len] + f"... ({len(obj):,} chars)"
        return obj

    @staticmethod
    def _try_as_json(value: object) -> str | None:
        """Try to pretty-print value as JSON. Returns formatted string or None."""
        import ast

        import numpy as np

        obj: object
        if isinstance(value, np.ndarray):
            obj = _normalize_json_like(value)
        elif isinstance(value, (dict, list)):
            obj = _normalize_json_like(value)
        elif isinstance(value, str):
            # Try JSON first, then Python repr
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(value)
                    if isinstance(parsed, (dict, list)):
                        obj = parsed
                        break
                except Exception:
                    continue
            else:
                return None
        else:
            return None
        obj = CellBrowserScreen._truncate_json_leaves(obj, CellBrowserScreen._MAX_JSON_LEAF)
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def _format_value(value: object) -> tuple[str, str | None]:
        """Return (display_text, language) for the cell value.

        Output is soft-capped at ``_MAX_DISPLAY_CHARS``; truncated text gets
        a footer pointing the user at `b` for full content (which goes
        through ``dump.serialize_cell``, bypassing this cap). Per-leaf
        truncation (``_MAX_JSON_LEAF``) keeps individual JSON strings
        bounded so pretty-printed JSON has short lines.
        """
        import pandas as pd_

        try:
            if value is None or pd_.isna(value):
                return "NULL", None
        except (TypeError, ValueError):
            pass

        if isinstance(value, (bytes, bytearray, memoryview)):
            from tabulaflow.cli.dump import sniff_binary

            raw = bytes(value)
            sniffed = sniff_binary(raw)
            label = sniffed[1] if sniffed else "binary"
            preview = raw[:32].hex(" ")
            return f"<{label}: {len(raw):,} bytes>\n{preview} ...", None

        # HuggingFace Image/Audio struct: surface the blob preview rather
        # than the JSON tree of ``{"bytes": ..., "path": ...}``. Matches the
        # serialize_cell path so the in-TUI cell view and the file written
        # by ``b`` are consistent (both treat the cell as media, not JSON).
        if isinstance(value, dict):
            inner = value.get("bytes")
            if isinstance(inner, (bytes, bytearray, memoryview)):
                from tabulaflow.cli.dump import sniff_binary

                raw = bytes(inner)
                sniffed = sniff_binary(raw)
                label = sniffed[1] if sniffed else "binary"
                preview = raw[:32].hex(" ")
                return f"<{label}: {len(raw):,} bytes>\n{preview} ...", None

        json_str = CellBrowserScreen._try_as_json(value)
        if json_str is not None:
            return CellBrowserScreen._cap_display(json_str), "json"

        s = str(value)
        if CellBrowserScreen._SQL_RE.match(s):
            return CellBrowserScreen._cap_display(s), "sql"
        if CellBrowserScreen._PY_RE.match(s):
            return CellBrowserScreen._cap_display(s), "python"
        return CellBrowserScreen._cap_display(s), None

    @classmethod
    def _cap_display(cls, text: str) -> str:
        """Truncate ``text`` to ``_MAX_DISPLAY_CHARS`` and append a footer."""
        if len(text) <= cls._MAX_DISPLAY_CHARS:
            return text
        return (
            text[: cls._MAX_DISPLAY_CHARS]
            + f"\n\n... (truncated to {cls._MAX_DISPLAY_CHARS:,} of {len(text):,} chars; "
            "press `b` for full content in browser)"
        )

    def _resolved_language(self) -> str | None:
        if self._language not in QueryBrowserScreen._SUPPORTED_LANGUAGES:
            return None
        if len(self._display_text) > self._MAX_HIGHLIGHT_CHARS:
            return None
        return self._language

    def _resolved_soft_wrap(self) -> bool:
        max_line = max((len(line) for line in self._display_text.split("\n")), default=0)
        return max_line < self._MAX_SOFT_WRAP_LINE

    def compose(self) -> ComposeResult:
        yield TextArea(
            self._display_text,
            language=self._resolved_language(),
            read_only=True,
            show_line_numbers=True,
            soft_wrap=self._resolved_soft_wrap(),
        )
        yield Static(classes="cell-browser-status")
        yield Static(classes="cell-browser-gap")
        yield Static(classes="cell-browser-hint")

    def on_mount(self) -> None:
        text_area = self.query_one(TextArea)
        text_area.register_theme(DRACULA_TRANSPARENT)
        text_area.theme = "dracula-transparent"
        self._refresh_status()

        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back    ", style="dim")
        hint.append("B", style=KEY_HINT)
        hint.append(" Open cell in browser    ", style="dim")
        self.query_one(".cell-browser-hint", Static).update(hint)

    def _refresh_status(self, extra: Text | None = None) -> None:
        status = Text()
        status.append(
            f"{self._column_name} ({self._dtype_str})  |  Row {self._row_number:,}",
            style="dim",
        )
        if extra is not None:
            status.append("  |  ", style="dim")
            status.append_text(extra)
        self.query_one(".cell-browser-status", Static).update(status)

    def action_close_browser(self) -> None:
        self.dismiss()

    async def action_open_in_browser(self) -> None:
        """Save the raw value with its native extension and open it in a browser.

        Uses ``webbrowser_open`` (which queries the system's default browser
        directly rather than going through file-extension associations) so
        ``.json`` reaches Chrome's native tree viewer regardless of how
        ``.json`` is otherwise associated. Falls back to reporting the
        saved path if no browser is available (headless / SSH).

        Shows ``Opening...`` while the serialize/write runs so the user
        sees an immediate response on click. Only paints the wait status
        when a dump is actually being produced — if the cached path
        already exists, the reuse-path is fast and skips the flicker.
        """
        if self._dumped_path is None or not self._dumped_path.exists():
            import asyncio

            self._refresh_status(Text("Opening...", style="dim"))
            painted: asyncio.Future[None] = asyncio.get_running_loop().create_future()
            self.call_after_refresh(lambda: painted.done() or painted.set_result(None))
            await painted
            path = open_cell_in_browser(self._raw_value, self.app, status=self._refresh_status)
            if path is None:
                return
            self._dumped_path = path
        else:
            _open_path_in_browser(self._dumped_path, status=self._refresh_status)


# ---------------------------------------------------------------------------
# Query browser screen
# ---------------------------------------------------------------------------


class QueryBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a query with scrolling."""

    DEFAULT_CSS = """
    QueryBrowserScreen {
        background: $background;
    }

    QueryBrowserScreen TextArea {
        height: 1fr;
        margin: 0 1;
        border: solid white;
        background: $background;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    QueryBrowserScreen TextArea:focus {
        border: solid white;
        outline: none;
    }

    QueryBrowserScreen .query-browser-gap {
        height: 1;
    }

    QueryBrowserScreen .query-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
    ]

    # Languages supported by Textual's TextArea.
    _SUPPORTED_LANGUAGES = frozenset(
        {
            "bash",
            "css",
            "go",
            "html",
            "java",
            "javascript",
            "json",
            "markdown",
            "python",
            "regex",
            "rust",
            "sql",
            "toml",
            "xml",
            "yaml",
        }
    )

    def __init__(self, *, title: str, query: str, lexer: str = "sql") -> None:
        super().__init__()
        self._title = title
        self._query = query
        self._lexer = lexer

    def compose(self) -> ComposeResult:
        lang = self._lexer if self._lexer in self._SUPPORTED_LANGUAGES else None
        yield TextArea(
            self._query,
            language=lang,
            read_only=True,
            show_line_numbers=True,
            soft_wrap=False,
        )
        yield Static(classes="query-browser-gap")
        yield Static(classes="query-browser-hint")

    def on_mount(self) -> None:
        text_area = self.query_one(TextArea)
        text_area.register_theme(DRACULA_TRANSPARENT)
        text_area.theme = "dracula-transparent"

        hint_text = Text()
        hint_text.append("Esc", style=KEY_HINT)
        hint_text.append(" Back    ", style="dim")
        self.query_one(".query-browser-hint", Static).update(hint_text)

    def action_close_browser(self) -> None:
        self.dismiss()


# ---------------------------------------------------------------------------
# Chart browser screen
# ---------------------------------------------------------------------------


class ChartBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a chart at terminal size."""

    DEFAULT_CSS = """
    ChartBrowserScreen {
        background: $background;
    }

    ChartBrowserScreen .chart-browser-content {
        height: 1fr;
        margin: 0 1;
        padding: 1 2;
        background: $background;
        color: $text;
    }

    ChartBrowserScreen .chart-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
    ]

    def __init__(self, *, title: str, df: "pd.DataFrame", vegalite_spec: dict[str, object]) -> None:
        super().__init__()
        self._title = title
        self._df = df
        self._vegalite_spec = vegalite_spec
        self._content = Static(classes="chart-browser-content")
        self._hint = Static(classes="chart-browser-hint")

    def compose(self) -> ComposeResult:
        yield self._content
        yield self._hint

    def on_mount(self) -> None:
        self._render_chart()

    def on_resize(self) -> None:
        self._render_chart()

    def action_close_browser(self) -> None:
        self.dismiss()

    def on_click(self, event: object) -> None:
        self.dismiss()

    def _render_chart(self) -> None:
        from tabulaflow.cli.display import build_chart

        content_width = max(20, self._content.size.width - 4)
        content_height = max(10, self._content.size.height)
        renderable = build_chart(self._df, self._vegalite_spec, content_width, content_height)
        self._content.update(renderable)

        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back    ", style="dim")
        self._hint.update(hint)


# ---------------------------------------------------------------------------
# Agent result widget with interactive tabs
# ---------------------------------------------------------------------------


class AgentResultWidget(Widget):
    """Displays an agent result with two-level tab switching.

    Top bar: records (shown when there is more than one record).
    Bottom bar: view kinds (Chart / Data / Query) for the selected record.
    """

    DEFAULT_CSS = """
    AgentResultWidget {
        padding: 1 1;
        margin: 1 4 0 1;
        height: auto;
        background: $surface;
    }

    AgentResultWidget.-focused {
        background: $focus-surface;
    }

    AgentResultWidget .top-bar-row {
        layout: horizontal;
        height: auto;
        margin: 0 0 1 0;
    }

    AgentResultWidget .record-bar {
        width: 1fr;
        height: auto;
        overflow-x: hidden;
        margin: 0 4 0 0;
    }

    AgentResultWidget .view-stepper {
        width: auto;
        height: auto;
    }

    AgentResultWidget .bottom-hint {
        height: auto;
    }

    """

    current_record: reactive[int] = reactive(0, init=False)
    current_view: reactive[int] = reactive(0, init=False)

    def __init__(
        self,
        result: ChatResult,
        width: int = 80,
        query_history: object | None = None,
    ) -> None:
        super().__init__()
        from tabulaflow.cli.display import build_result_views
        from tabulaflow.toolhub.query_history import QueryHistory

        self._records = build_result_views(result, width)
        self._query_history: QueryHistory | None = query_history if isinstance(query_history, QueryHistory) else None
        self._content = Static(id="result-content")
        self._mounted = False
        self._record_bar_widget: Static | None = None
        self._view_stepper_widget: Static | None = None
        self._bottom_hint_widget: Static | None = None
        # Record hit areas: (record_index, col_start, col_end, row) relative
        # to the record bar widget. Pills wrap across multiple rows when they
        # don't all fit on a single line.
        self._record_hit_areas: list[tuple[int, int, int, int]] = []
        # View hit areas: (target, col_start, col_end) relative to the view
        # stepper widget. Target is "prev" or "next".
        self._view_hit_areas: list[tuple[str, int, int]] = []

    @property
    def _has_top_bar(self) -> bool:
        """Top bar exists whenever the result has any displayable records."""
        return bool(self._records)

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal

        if self._has_top_bar:
            self._record_bar_widget = Static(classes="record-bar")
            self._view_stepper_widget = Static(classes="view-stepper")
            yield Horizontal(
                self._record_bar_widget,
                self._view_stepper_widget,
                classes="top-bar-row",
            )
        yield self._content
        if self._has_top_bar:
            self._bottom_hint_widget = Static(classes="bottom-hint")
            yield self._bottom_hint_widget

    def on_mount(self) -> None:
        self._mounted = True
        self._refresh_all()

    def on_resize(self) -> None:
        if self._record_bar_widget is not None:
            self._update_record_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()

    def watch_current_record(self) -> None:
        if not self._mounted:
            return
        # Clamp current_view to the new record's view count; setting it will
        # trigger watch_current_view which calls _refresh_all.
        rec = self._current_record_or_none()
        if rec is not None and self.current_view >= len(rec.views):
            self.current_view = max(0, len(rec.views) - 1)
            return
        self._refresh_all()

    def watch_current_view(self) -> None:
        if not self._mounted:
            return
        self._refresh_all()

    def watch_has_focus(self, has_focus: bool) -> None:
        """Re-render styled elements when focus changes.

        The record pill, view stepper chevrons / kind label, and the
        ``KEY_HINT`` glyphs use mint accents when this widget is focused
        and a muted gray when it isn't — the focus indication emerges
        from element saturation rather than added chrome (no border,
        stripe, or glyph). Modern app pattern (Linear, VS Code panels).
        """
        self.set_class(has_focus, "-focused")
        if not self._mounted:
            return
        if self._record_bar_widget is not None:
            self._update_record_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()

    @property
    def _focus_accent(self) -> str:
        return ACCENT if self.has_focus else ACCENT_DIM

    @property
    def _focus_key_hint(self) -> str:
        return KEY_HINT if self.has_focus else KEY_HINT_DIM

    def _refresh_all(self) -> None:
        self._update_content()
        if self._record_bar_widget is not None:
            self._update_record_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()
        if self._is_last_chat_item():
            chat_log = self.app.query_one("#chat-log")
            chat_log.scroll_end(animate=False)

    def _is_last_chat_item(self) -> bool:
        """Return True when this widget is the last chat log child."""
        try:
            chat_log = self.app.query_one("#chat-log")
        except Exception:
            return False
        children = list(chat_log.children)
        return bool(children) and children[-1] is self

    def _current_record_or_none(self) -> "RecordGroup | None":
        if not self._records:
            return None
        idx = min(self.current_record, len(self._records) - 1)
        return self._records[idx]

    def _current_view_or_none(self) -> "ViewItem | None":
        rec = self._current_record_or_none()
        if rec is None or not rec.views:
            return None
        idx = min(self.current_view, len(rec.views) - 1)
        return rec.views[idx]

    def _update_record_bar(self) -> None:
        """Render record pills left-anchored, wrapping across multiple lines.

        All pills are shown; when the row fills, subsequent pills wrap to a
        new line. When more than one record exists, a ``·  ←/→ Switch record``
        hint is appended inline after the final pill if it fits on the last
        line, otherwise on a new line below.

        Hit areas are stored as ``(record_index, col_start, col_end, row)``
        relative to ``self._record_bar_widget`` so the click handler can test
        ``event.x``/``event.y`` directly without worrying about the enclosing
        layout.
        """
        from rich.style import Style

        if self._record_bar_widget is None:
            return

        available_width = self._record_bar_widget.size.width or 80
        record_interactive = len(self._records) > 1

        HINT_SEP = " · "
        HINT_KEY = "←/→"
        HINT_TEXT = " Switch record"
        hint_width = len(HINT_SEP) + len(HINT_KEY) + len(HINT_TEXT) if record_interactive else 0

        SEP = 1  # space between pills on the same row
        dim_style = Style(dim=True)

        line = Text(no_wrap=True, overflow="crop")
        self._record_hit_areas = []
        row = 0
        col = 0

        for rec_idx, r in enumerate(self._records):
            pill = f" {r.label} "
            pill_width = len(pill)
            needed = pill_width + (SEP if col > 0 else 0)
            if col > 0 and col + needed > available_width:
                line.append("\n")
                row += 1
                col = 0
                needed = pill_width
            if col > 0:
                line.append(" ")
                col += 1
            col_start = col
            pill_style = (
                Style(bold=True, color="black", bgcolor=self._focus_accent)
                if rec_idx == self.current_record
                else Style(dim=True)
            )
            line.append_text(Text(pill, style=pill_style))
            col += pill_width
            self._record_hit_areas.append((rec_idx, col_start, col, row))

        if record_interactive:
            if col + hint_width > available_width:
                line.append("\n")
            line.append_text(Text(HINT_SEP, style=dim_style))
            line.append_text(Text("←", style=self._focus_key_hint))
            line.append_text(Text("/", style="dim"))
            line.append_text(Text("→", style=self._focus_key_hint))
            line.append_text(Text(HINT_TEXT, style="dim"))

        self._record_bar_widget.update(line)

    def _update_view_stepper(self) -> None:
        """Render the view stepper with an optional switch-view hint on its left.

        Hit areas are stored relative to ``self._view_stepper_widget``.
        """
        from rich.style import Style

        from tabulaflow.cli.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

        if self._view_stepper_widget is None:
            return

        rec = self._current_record_or_none()
        has_views = rec is not None and bool(rec.views)
        view_interactive = rec is not None and len(rec.views) > 1

        self._view_hit_areas = []
        if not has_views:
            self._view_stepper_widget.update(Text(""))
            return
        assert rec is not None

        chevron_style = Style(bold=True, color=self._focus_accent)
        label_style = Style(bold=True, color=self._focus_accent)
        dim_sep_style = Style(dim=True)

        cur_kind = rec.views[min(self.current_view, len(rec.views) - 1)].kind
        max_kind_width = max(len(k) for k in (VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY))
        pad = max_kind_width - len(cur_kind)

        line = Text(no_wrap=True)
        col = 0

        # Always reserve the Switch view hint width so the stepper's total
        # width stays constant across records. If we rendered this block only
        # when the record has multiple views, clicking a single-view record
        # would shrink the stepper and — since it shares a row with the
        # ``width: 1fr`` record bar — cause the record pills to re-wrap.
        if view_interactive:
            line.append_text(Text("[", style=self._focus_key_hint))
            line.append_text(Text("/", style="dim"))
            line.append_text(Text("]", style=self._focus_key_hint))
            col += 3
            line.append_text(Text(" Switch view", style="dim"))
            col += len(" Switch view")
            line.append_text(Text(" · ", style=dim_sep_style))
            col += 3
        else:
            reserved = 3 + len(" Switch view") + 3
            line.append_text(Text(" " * reserved))
            col += reserved

        # Left-pad short kinds outside the stepper so the stepper itself stays
        # visually tight and its right edge stays pinned.
        if pad > 0:
            line.append_text(Text(" " * pad))
            col += pad

        prev_x = col
        if view_interactive:
            line.append_text(Text("◂", style=chevron_style))
        else:
            line.append_text(Text(" "))
        col += 1
        line.append_text(Text(" "))
        col += 1
        line.append_text(Text(cur_kind, style=label_style))
        col += len(cur_kind)
        line.append_text(Text(" "))
        col += 1
        next_x = col
        if view_interactive:
            line.append_text(Text("▸", style=chevron_style))
        else:
            line.append_text(Text(" "))
        col += 1

        if view_interactive:
            self._view_hit_areas.append(("prev", prev_x, prev_x + 1))
            self._view_hit_areas.append(("next", next_x, next_x + 1))

        self._view_stepper_widget.update(line)

    def _update_bottom_hint(self) -> None:
        """Render hint affordances below the preview.

        The hint cluster is right-aligned. For data views, the truncation
        caption ('showing N of M rows/cols') is left-aligned on the same
        line. Hints read left-to-right as the user's natural progression:
        navigate to a record (↑↓), then inspect it (Enter).
        """
        if self._bottom_hint_widget is None:
            return
        view = self._current_view_or_none()
        if view is None:
            self._bottom_hint_widget.update(Text(""))
            return

        hint = Text(no_wrap=True)
        # ↑↓ and Enter only do anything when this widget is focused, so
        # both follow focus-state dimming (bright when focused, dim when
        # not) — the "way in" comes from the docked bottom-bar hint, not
        # from the widget itself.
        hint.append("↑↓", style=self._focus_key_hint)
        hint.append(" Prev/Next result    ", style="dim")
        hint.append("↵", style=self._focus_key_hint)
        hint.append(" Inspect", style="dim")

        caption = self._data_preview_caption(view)
        available = self._bottom_hint_widget.size.width or 0
        line = Text(no_wrap=True)
        if caption:
            line.append(caption, style="dim")
            pad = available - hint.cell_len - len(caption)
        else:
            pad = available - hint.cell_len
        line.append(" " * max(1, pad))
        line.append_text(hint)
        self._bottom_hint_widget.update(line)

    def _data_preview_caption(self, view: "ViewItem") -> str:
        """Return the truncation caption for a data view, or empty string."""
        from tabulaflow.cli.display import VIEW_KIND_DATA

        if view.kind != VIEW_KIND_DATA or view.data_shape is None:
            return ""
        num_rows, num_cols = view.data_shape
        shown_cols = view.shown_cols if view.shown_cols is not None else num_cols
        parts: list[str] = []
        if num_rows > DATA_PREVIEW_MAX_ROWS:
            parts.append(f"showing {DATA_PREVIEW_MAX_ROWS} of {num_rows} rows")
        if num_cols > shown_cols:
            parts.append(f"showing {shown_cols} of {num_cols} columns")
        return " | ".join(parts)

    def _update_content(self) -> None:
        view = self._current_view_or_none()
        if view is None:
            self._content.update(Text("No results to display.", style="dim"))
            return
        self._content.update(view.renderable)

    def on_click(self, event: object) -> None:
        """Handle clicks on tab labels and content regions."""
        from textual.events import Click

        assert isinstance(event, Click)

        if self._record_bar_widget is not None and event.widget is self._record_bar_widget:
            for rec_idx, col_start, col_end, row in self._record_hit_areas:
                if row == event.y and col_start <= event.x < col_end:
                    if rec_idx != self.current_record:
                        self._switch_record(rec_idx)
                    return
            return

        if self._view_stepper_widget is not None and event.widget is self._view_stepper_widget:
            if event.y != 0:
                return
            for target, col_start, col_end in self._view_hit_areas:
                if col_start <= event.x < col_end:
                    if target == "prev":
                        self.action_prev_view()
                    elif target == "next":
                        self.action_next_view()
                    return
            return

        if event.widget is self._content:
            view = self._current_view_or_none()
            if view is None:
                return
            from tabulaflow.cli.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

            if view.kind == VIEW_KIND_CHART and self._is_chart_region_click(view, event.x, event.y):
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return
            if view.kind == VIEW_KIND_DATA and self._is_table_region_click(view, event.x, event.y):
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return
            if view.kind == VIEW_KIND_QUERY:
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return

    def _is_chart_region_click(self, view: "ViewItem", x: int, y: int) -> bool:
        """Return True when click lands within the rendered chart area."""
        if x < 0 or y < 0:
            return False
        options = self.app.console.options.update(width=max(1, self._content.size.width))
        measurement = self.app.console.measure(view.renderable, options=options)
        return bool(x < measurement.maximum)

    def _is_table_region_click(self, view: "ViewItem", x: int, y: int) -> bool:
        """Return True when click lands within the visible data-table preview area."""
        if x < 0 or y < 0:
            return False
        content_height = self._content.size.height
        if content_height <= 0:
            return False
        table_width = self._data_preview_table_width(view)
        if table_width <= 0 or x >= table_width:
            return False
        return y < content_height

    def _data_preview_table_width(self, view: "ViewItem") -> int:
        """Measure rendered width of the data preview table area."""
        options = self.app.console.options.update(width=max(1, self._content.size.width))
        measurement = self.app.console.measure(view.renderable, options=options)
        return int(measurement.maximum)

    def _switch_record(self, new_idx: int) -> None:
        """Change the active record, preserving the current view kind if possible."""
        if not self._records or new_idx == self.current_record:
            return
        current_view = self._current_view_or_none()
        target_kind = current_view.kind if current_view is not None else None
        new_rec = self._records[new_idx]
        new_view_idx = 0
        if target_kind is not None:
            for i, v in enumerate(new_rec.views):
                if v.kind == target_kind:
                    new_view_idx = i
                    break
        self.current_record = new_idx
        self.current_view = new_view_idx

    def action_next_view(self) -> None:
        rec = self._current_record_or_none()
        if rec is not None and len(rec.views) > 1:
            self.current_view = (self.current_view + 1) % len(rec.views)

    def action_prev_view(self) -> None:
        rec = self._current_record_or_none()
        if rec is not None and len(rec.views) > 1:
            self.current_view = (self.current_view - 1) % len(rec.views)

    def action_next_record(self) -> None:
        if len(self._records) > 1:
            self._switch_record((self.current_record + 1) % len(self._records))

    def action_prev_record(self) -> None:
        if len(self._records) > 1:
            self._switch_record((self.current_record - 1) % len(self._records))

    can_focus = True

    BINDINGS = [
        ("right_square_bracket", "next_view", "Next view"),
        ("left_square_bracket", "prev_view", "Previous view"),
        ("right", "next_record", "Next record"),
        ("left", "prev_record", "Previous record"),
        ("enter", "open_full_screen", "Full screen"),
        # ``priority=True`` so these beat ``VerticalScroll``'s own priority
        # up/down bindings (which would otherwise scroll the chat log
        # instead of moving between focused result widgets).
        Binding("up", "focus_prev_result", "Previous result", priority=True),
        Binding("down", "focus_next_result", "Next result", priority=True),
        ("escape", "focus_input", "Back to input"),
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
        """Focus the next AgentResultWidget, or return to the input.

        When the user is on the newest result and presses ``down``, focus
        jumps back to the input bar — completing the "step back through
        history, step forward back to input" chain.
        """
        results = list(self.app.query(AgentResultWidget))
        try:
            idx = results.index(self)
        except ValueError:
            return
        if idx < len(results) - 1:
            results[idx + 1].focus()
            results[idx + 1].scroll_visible()
        else:
            self.app.query_one("#input-bar").focus()

    def action_focus_input(self) -> None:
        """Return focus to the input bar."""
        self.app.query_one("#input-bar").focus()

    async def action_open_full_screen(self) -> None:
        """Open full-screen viewer for the active Chart, Data, or Query tab."""
        from tabulaflow.cli.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

        rec = self._current_record_or_none()
        view = self._current_view_or_none()
        if rec is None or view is None:
            return
        title = f"{view.kind} ({rec.label})"

        if view.kind == VIEW_KIND_CHART and view.chart_spec is not None:
            df = await self._fetch_df(rec.record_id)
            if df is not None:
                self.app.push_screen(ChartBrowserScreen(title=title, df=df, vegalite_spec=view.chart_spec))
            return
        if view.kind == VIEW_KIND_DATA:
            df = await self._fetch_df(rec.record_id)
            if df is not None:
                self.app.push_screen(DataBrowserScreen(title=title, df=df))
            return
        if view.kind == VIEW_KIND_QUERY and view.query is not None:
            query, lexer = view.query
            self.app.push_screen(QueryBrowserScreen(title=title, query=query, lexer=lexer))

    async def _fetch_df(self, record_id: str) -> pd.DataFrame | None:
        """Fetch a DataFrame from QueryHistory, hydrating from DuckDB if needed."""
        if self._query_history is None:
            return None
        try:
            record = await self._query_history.get(record_id)
        except (KeyError, ValueError):
            return None
        if record.pred_query.exec_result is None:
            return None
        return record.pred_query.exec_result.df


# ---------------------------------------------------------------------------
# Schema browser screen
# ---------------------------------------------------------------------------

# Node data stored in Tree nodes to identify what each node represents.
_NODE_KIND_DB = "db"
_NODE_KIND_SCHEMA = "schema"
_NODE_KIND_TABLE = "table"
_NODE_KIND_COLUMN = "column"


class _NodeData:
    """Metadata attached to each Tree node."""

    __slots__ = ("kind", "alias", "schema_name", "table_name", "column_name")

    def __init__(
        self,
        kind: str,
        alias: str,
        schema_name: str | None = None,
        table_name: str | None = None,
        column_name: str | None = None,
    ) -> None:
        self.kind = kind
        self.alias = alias
        self.schema_name = schema_name
        self.table_name = table_name
        self.column_name = column_name


# 4-tuple identifier for any tree node: (alias, schema, table, column).
# DB → (a, None, None, None); schema → (a, s, None, None); table → (a, s, t,
# None); column → (a, s, t, c). All four levels are unique by tuple identity.
_NodePath = tuple[str, str | None, str | None, str | None]


class _ExplorerState:
    """Session-scoped UI state for ``SchemaBrowserScreen``.

    Held on ``TabulaflowApp`` and passed by reference into each freshly-created
    schema browser. The screen reads ``expansion`` while building nodes
    and updates state continuously via tree event handlers — no
    snapshot-on-close step needed.

    ``expansion`` is a *dict*, not a set: presence of a path means "the
    user has seen this node," and the value is its expansion state.
    Unknown paths fall through to the build-time default. This is what
    distinguishes "user explicitly collapsed" (path → False) from "user
    never saw this node" (path absent → use default), so newly-connected
    DBs honor their auto-expand default instead of being collapsed by
    a missing entry.
    """

    __slots__ = ("expansion", "cursor")

    def __init__(self) -> None:
        self.expansion: dict[_NodePath, bool] = {}
        self.cursor: _NodePath | None = None


class SchemaBrowserScreen(Screen[None]):
    """Full-screen tree browser for exploring connected database schemas."""

    DEFAULT_CSS = """
    SchemaBrowserScreen {
        background: $background;
    }

    SchemaBrowserScreen #browse-tree {
        height: 1fr;
        padding: 1 2;
        background: $background;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    SchemaBrowserScreen #browse-tree:focus {
        outline: none;
        background-tint: transparent 0%;
    }

    SchemaBrowserScreen #browse-tree:focus > .tree--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    SchemaBrowserScreen #browse-tree > .tree--highlight {
        background: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--highlight-line {
        background: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides-hover {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides-selected {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree:focus > .tree--guides-selected {
        color: #555555;
    }

    SchemaBrowserScreen .schema-browser-status {
        padding: 0 2;
        color: #f5f5f5;
    }

    SchemaBrowserScreen .schema-browser-gap {
        height: 1;
    }

    SchemaBrowserScreen #browse-hint {
        dock: bottom;
        padding: 0 2;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("left", "collapse_node", "Collapse", show=False, priority=True),
        Binding("right", "expand_node", "Expand", show=False, priority=True),
        Binding("enter", "open_preview", "Preview table", show=False, priority=True),
    ]

    _PREVIEW_ROW_CAP = 50

    def __init__(
        self,
        *,
        registry: object,
        alias: str | None = None,
        state: _ExplorerState | None = None,
    ) -> None:
        super().__init__()
        from tabulaflow.core.db_connector.db_registry import DBRegistry

        assert isinstance(registry, DBRegistry)
        self._registry: DBRegistry = registry
        self._filter_alias = alias
        self._state = state if state is not None else _ExplorerState()
        self._status = Static(classes="schema-browser-status")
        self._gap = Static(classes="schema-browser-gap")
        self._hint = Static(id="browse-hint")

    def compose(self) -> ComposeResult:
        from textual.widgets import Tree

        tree: Tree[_NodeData] = Tree("Databases", id="browse-tree")
        tree.show_root = False
        tree.guide_depth = 3
        tree.auto_expand = False

        yield tree
        yield self._status
        yield self._gap
        yield self._hint

    def on_mount(self) -> None:
        # Snapshot the saved cursor before any side effects can clobber it.
        # ``on_tree_node_highlighted`` rewrites ``_state.cursor`` whenever
        # the cursor moves, including the implicit move that Textual does
        # to the first line on initial render — without this local, that
        # would overwrite the path we're about to restore to.
        saved_cursor = self._state.cursor
        self._build_tree()
        self._update_status()
        self._update_hint()
        tree = self.query_one("#browse-tree")
        tree.focus()
        # Cursor restore is deferred to after the next refresh: ancestor
        # expansion (built into the tree but applied lazily by Textual)
        # only populates ``_tree_lines`` on render. Running ``move_cursor``
        # before that leaves it as a silent no-op for collapsed-by-default
        # subtrees (the workspace alias case).
        if saved_cursor is not None:
            self.call_after_refresh(self._restore_cursor, saved_cursor)
        elif not self._state.expansion:
            # Genuine first open — nothing to restore, focus the first
            # table so Enter previews immediately.
            self.call_after_refresh(self._focus_first_table)

    @staticmethod
    def _node_path(data: "_NodeData | None") -> _NodePath | None:
        if data is None:
            return None
        return (data.alias, data.schema_name, data.table_name, data.column_name)

    def _expand_for(self, path: _NodePath, default: bool) -> bool:
        """Resolve expansion state for a node: the user's last-recorded
        value if known, otherwise the construction-time default.
        """
        return self._state.expansion.get(path, default)

    def _walk_nodes(self) -> "Iterator[Any]":
        """Pre-order traversal of every tree node below the (hidden) root."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        stack: list[Any] = list(reversed(tree.root.children))
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def _find_node_by_path(self, path: _NodePath) -> "Any | None":
        for node in self._walk_nodes():
            if self._node_path(node.data) == path:
                return node
        return None

    def _first_table_node(self) -> "Any | None":
        for node in self._walk_nodes():
            data: _NodeData | None = node.data
            if data is not None and data.kind == _NODE_KIND_TABLE:
                return node
        return None

    def _restore_cursor(self, saved: _NodePath | None) -> None:
        """Move the cursor to the saved node, if its path still resolves.

        Deliberately does not fall back to the first table or force
        ancestor expansion when the path is missing — the build phase
        already put the tree in the user's saved collapse state, and
        overriding that to make a fallback cursor visible would silently
        undo an explicit collapse (e.g., after a disconnect dropped the
        saved cursor's DB).
        """
        if saved is None:
            return
        target = self._find_node_by_path(saved)
        if target is None:
            return
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        tree.move_cursor(target)
        tree.scroll_to_node(target)

    def _focus_first_table(self) -> None:
        """First-open default: land the cursor on the first table so Enter
        previews immediately. Force-expands ancestors because on a true
        first open there is no user-intended collapse state to respect.
        """
        target = self._first_table_node()
        if target is None:
            return
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        parent = target.parent
        while parent is not None and parent is not tree.root:
            parent.expand()
            parent = parent.parent
        tree.move_cursor(target)
        tree.scroll_to_node(target)

    # -- event handlers: keep ``_state`` current as the user navigates ----

    def on_tree_node_expanded(self, event: "Any") -> None:
        path = self._node_path(event.node.data)
        if path is not None:
            self._state.expansion[path] = True

    def on_tree_node_collapsed(self, event: "Any") -> None:
        path = self._node_path(event.node.data)
        if path is not None:
            self._state.expansion[path] = False

    # -- tree construction ---------------------------------------------------

    def _build_tree(self) -> None:
        from textual.widgets import Tree

        from tabulaflow.schema import SQLSchema, SQLTableSchema

        tree = self.query_one("#browse-tree", Tree)

        aliases = self._registry.list_aliases()
        if self._filter_alias is not None:
            aliases = [a for a in aliases if a == self._filter_alias]
        aliases.sort()

        for alias in aliases:
            connector = self._registry.get(alias)
            schema = connector.schema
            if not isinstance(schema, SQLSchema):
                continue

            db_label = Text()
            db_label.append(alias, style="bold")
            dialect = schema.dialect or getattr(connector, "language", None)
            if dialect:
                db_label.append(f"  {dialect}", style="dim")

            auto_expand = alias != "workspace"
            db_node = tree.root.add(
                db_label,
                data=_NodeData(kind=_NODE_KIND_DB, alias=alias),
                expand=self._expand_for((alias, None, None, None), auto_expand),
            )

            tables: list[SQLTableSchema] = list(schema.tables)
            schema_names: set[str | None] = {t.schema_name for t in tables}
            has_schemas = schema_names != {None}

            if has_schemas:
                groups: dict[str | None, list[SQLTableSchema]] = {}
                for t in tables:
                    groups.setdefault(t.schema_name, []).append(t)
                for sn in sorted(groups, key=lambda s: (s is None, s or "")):
                    sn_label = Text()
                    sn_label.append(sn or "(default)", style="bold")
                    schema_node = db_node.add(
                        sn_label,
                        data=_NodeData(kind=_NODE_KIND_SCHEMA, alias=alias, schema_name=sn),
                        expand=self._expand_for((alias, sn, None, None), auto_expand),
                    )
                    for t in sorted(groups[sn], key=lambda t: t.name):
                        self._add_table_node(schema_node, alias, t)
            else:
                for t in sorted(tables, key=lambda t: t.name):
                    self._add_table_node(db_node, alias, t)

    def _add_table_node(self, parent: object, alias: str, table: object) -> None:
        from tabulaflow.schema import SQLTableSchema

        assert isinstance(table, SQLTableSchema)
        parent_node: Any = parent

        t_label = Text()
        t_label.append(table.name)
        if table.is_view:
            t_label.append("  view", style="dim")

        table_node = parent_node.add(
            t_label,
            data=_NodeData(
                kind=_NODE_KIND_TABLE,
                alias=alias,
                schema_name=table.schema_name,
                table_name=table.name,
            ),
            expand=self._expand_for((alias, table.schema_name, table.name, None), False),
        )

        for col in table.columns:
            c_label = Text()
            c_label.append(col.name)
            c_label.append(f"  {col.dtype}", style="dim")
            if col.primary_key_type:
                c_label.append(" PK", style="bold #e6c07b")
            if col.foreign_keys:
                c_label.append(" FK", style="#61afef")
            table_node.add_leaf(
                c_label,
                data=_NodeData(
                    kind=_NODE_KIND_COLUMN,
                    alias=alias,
                    schema_name=table.schema_name,
                    table_name=table.name,
                    column_name=col.name,
                ),
            )

    # -- actions --------------------------------------------------------------

    async def action_open_preview(self) -> None:
        """Open DataBrowserScreen for the table under the cursor.

        For writable SQL connectors (``read_only=False``), runs a live
        ``SELECT * ... LIMIT 10`` so the preview reflects the current
        database state.  For read-only or non-SQL connectors, falls back
        to the cached ``sampled_df``.
        """
        from textual.widgets import Tree

        from tabulaflow.schema import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node_data: _NodeData | None = node.data
        if node_data is None or node_data.kind != _NODE_KIND_TABLE:
            return

        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        assert isinstance(schema, SQLSchema)
        # SQLSchema implies a SQL connector; the live preview path uses
        # SQLAlchemy ``Executable`` which only ``BaseSQLDBConnector``
        # accepts.
        assert connector.connector_type == "sql"
        assert node_data.table_name is not None
        table = next(
            (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
            None,
        )
        if table is None:
            return

        import pandas as pd
        import sqlalchemy

        tbl = sqlalchemy.table(
            node_data.table_name,
            schema=node_data.schema_name,
        )
        stmt = sqlalchemy.select("*").select_from(tbl).limit(self._PREVIEW_ROW_CAP)
        self._status.update(Text("Loading preview...", style="dim"))
        result = await connector.run_query_async(stmt, timeout=30)
        if result.error is not None:
            msg = result.error.message.replace("\n", " ").strip()
            self._status.update(Text.from_markup(f"[red]Preview error:[/red] {msg}"))
            return
        self._update_status()
        df = result.df if result.df is not None else pd.DataFrame()

        suffix = f"(first {self._PREVIEW_ROW_CAP} rows)"
        title = (
            f"{node_data.alias}: {node_data.schema_name}.{node_data.table_name} {suffix}"
            if node_data.schema_name
            else f"{node_data.alias}: {node_data.table_name} {suffix}"
        )
        self.app.push_screen(DataBrowserScreen(title=title, df=df))

    # -- actions & hints -----------------------------------------------------

    def action_close_browser(self) -> None:
        self.dismiss()

    def action_collapse_node(self) -> None:
        """Collapse the cursor node."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node.collapse()

    def action_expand_node(self) -> None:
        """Expand the cursor node."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node.expand()

    def on_tree_node_highlighted(self, event: "Any") -> None:
        """Update hint/status bars and record cursor position in state."""
        self._state.cursor = self._node_path(event.node.data)
        self._update_status()
        self._update_hint()

    def _cursor_has_preview(self) -> bool:
        """Return True if the cursor is on a table node with sampled_df."""
        from textual.widgets import Tree

        from tabulaflow.schema import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return False
        node_data: _NodeData | None = node.data
        if node_data is None or node_data.kind != _NODE_KIND_TABLE:
            return False
        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            return False
        table = next(
            (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
            None,
        )
        return table is not None and table.sampled_df is not None and not table.sampled_df.empty

    def _update_status(self) -> None:
        """Update the status bar with table/column/row counts for the highlighted scope."""
        from textual.widgets import Tree

        from tabulaflow.schema import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            self._status.update(Text(""))
            return

        node_data: _NodeData | None = node.data
        if node_data is None:
            self._status.update(Text(""))
            return

        parts: list[str] = []
        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            self._status.update(Text(""))
            return

        if node_data.kind == _NODE_KIND_DB:
            tables = list(schema.tables)
            parts.append(node_data.alias)
            parts.append(f"{len(tables):,} tables")

        elif node_data.kind == _NODE_KIND_SCHEMA:
            tables = [t for t in schema.tables if t.schema_name == node_data.schema_name]
            path = f"{node_data.alias} > {node_data.schema_name or '(default)'}"
            parts.append(path)
            parts.append(f"{len(tables):,} tables")

        elif node_data.kind in (_NODE_KIND_TABLE, _NODE_KIND_COLUMN):
            table = next(
                (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
                None,
            )
            if table:
                if node_data.schema_name:
                    path = f"{node_data.alias} > {node_data.schema_name}.{node_data.table_name}"
                else:
                    path = f"{node_data.alias} > {node_data.table_name}"
                parts.append(path)
                parts.append(f"{len(table.columns):,} columns")
                if table.num_rows is not None:
                    parts.append(f"{table.num_rows:,} rows")

        if parts:
            self._status.update(Text("  |  ".join(parts), style="dim"))
        else:
            self._status.update(Text(""))

    def _update_hint(self) -> None:
        hint_fg = "dim"
        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back", style=hint_fg)
        if self._cursor_has_preview():
            hint.append("    ", style=hint_fg)
            hint.append("↵", style=KEY_HINT)
            hint.append(" Preview table", style=hint_fg)
        self._hint.update(hint)
