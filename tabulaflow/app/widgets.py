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
from textual.suggester import Suggester
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Input, Static

from tabulaflow.app.theme import ACCENT
from tabulaflow.chat import (
    ChatEvent,
    ColumnsReturned,
    Failed,
    Finished,
    RowsReturned,
    TextDelta,
    ThinkingDelta,
    ToolFinished,
    ToolOutcome,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)


if TYPE_CHECKING:
    from rich.console import RenderableType

    from tabulaflow.chat import ChatResult
    from tabulaflow.core.types import Usage


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
        from tabulaflow.app.display import build_banner

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
# Agent progress widget (consumes the ChatAgent event stream)
# ---------------------------------------------------------------------------


def summarize_tool_args(name: str, args: dict[str, object]) -> str:
    """Render a tool call's raw args as a compact one-line label for the TUI.

    Presentation lives here (the consumer), not in ``chat`` — the events carry the
    raw ``args`` dict and each frontend renders it as it likes. Truncates the query
    to keep the step line short."""
    db_prefix = f"[{args['db_alias']}] " if args.get("db_alias") else ""

    if name == "run_query":
        query = " ".join(str(args.get("query", "")).split())
        if len(query) > 40:
            query = query[:37] + "..."
        return f"{db_prefix}{query}"
    if name == "get_table_schema":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        return f"{db_prefix}{'.'.join(parts)}"
    if name == "get_db_document":
        return f"{db_prefix}{'refresh' if args.get('refresh') else 'cached'}"
    if name == "get_column_json_schema":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        parts.append(str(args.get("column_name", "")))
        label = ".".join(parts)
        if args.get("path"):
            label += f", path={args['path']}"
        return f"{db_prefix}{label}"
    if name == "render_chart":
        spec_str = args.get("vegalite_spec", "")
        try:
            spec = json.loads(spec_str) if isinstance(spec_str, str) else spec_str
            mark = spec.get("mark", "") if isinstance(spec, dict) else ""
            if isinstance(mark, dict):
                mark = mark.get("type", "")
            title = spec.get("title", "") if isinstance(spec, dict) else ""
            return str(title) if title else str(mark)
        except (json.JSONDecodeError, TypeError):
            return "chart"
    if name == "transfer_record":
        record_id = str(args.get("record_id", ""))
        target_alias = str(args.get("target_alias", ""))
        target_schema = str(args.get("target_schema", "")) if args.get("target_schema") else ""
        target_table = str(args.get("target_table", ""))
        mode = str(args.get("mode", "append"))
        target = f"{target_schema}.{target_table}" if target_schema else target_table
        return f"{record_id} -> [{target_alias}] {target} ({mode})"
    if name == "run_subagent_for_each_row":
        return f"{db_prefix}{args.get('table_name', '')}"
    return str(args)[:80] if args else ""


def summarize_outcome(outcome: ToolOutcome) -> str:
    """Render a structured tool outcome as the TUI's default one-line label."""
    if isinstance(outcome, RowsReturned):
        return f"{outcome.count} rows"
    if isinstance(outcome, ColumnsReturned):
        return f"{outcome.count} columns"
    if isinstance(outcome, Failed):
        return "error"
    return "done"  # Completed


class AgentProgressWidget(Widget):
    """Shows agent execution progress with tool steps and streaming text.

    Driven by ``apply(event)`` over the ``ChatAgent.run_stream`` event stream; the
    consumer (``tui._run_agent``) calls ``mark_interrupted`` on cancellation."""

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
        self._thinking_text = ""
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

        if self._thinking_text and not self._streaming_text and not self._frozen:
            if self._steps:
                parts.append(Text())
            parts.append(Text(self._thinking_text, style="dim italic"))

        if self._streaming_text:
            if self._steps:
                parts.append(Text())
            parts.append(Text(self._streaming_text))

        return Group(*parts) if parts else Text()

    # Event-stream consumption

    def apply(self, event: ChatEvent) -> None:
        """Dispatch one ``ChatEvent`` from ``ChatAgent.run_stream`` to the renderer."""
        if isinstance(event, ToolStarted):
            self._on_tool_start(event.tool_call_id, event.name, summarize_tool_args(event.name, event.args))
        elif isinstance(event, ToolFinished):
            self._on_tool_end(event.tool_call_id, event.name, summarize_outcome(event.outcome))
        elif isinstance(event, ToolProgress):
            self._on_tool_progress(event.completed, event.total, event.stage)
        elif isinstance(event, TextDelta):
            self._on_text_delta(event.content)
        elif isinstance(event, ThinkingDelta):
            self._on_thinking_delta(event.content)
        elif isinstance(event, UsageUpdated):
            self._on_usage(event.usage)
        elif isinstance(event, Finished):
            self._on_finished(event.result)

    def _on_finished(self, result: ChatResult) -> None:
        # Reconcile the live-streamed prose with the authoritative final text, then
        # freeze. (The terminal Finished event carries the full ChatResult.)
        if self._streaming_text != result.text:
            self._streaming_text = result.text
        if result.usage is not None:
            self._usage = result.usage
        self._status_text = None
        self._frozen = True
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._refresh(layout=True)

    def mark_interrupted(self, usage: Usage | None = None) -> None:
        """Freeze the widget after a cancelled run (the consumer calls this on
        ``CancelledError``; no terminal ``Finished`` arrives for an interrupt)."""
        if usage is not None:
            self._usage = usage
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

    def _on_tool_start(self, tool_call_id: str, name: str, args_summary: str) -> None:
        if self._status_text and self._status_text != "Thinking...":
            self._steps.append(("done", "", "__status__", self._status_text))
        label = f"{name}({args_summary})" if args_summary else name
        self._steps.append(("running", tool_call_id, name, label))
        self._streaming_text = ""
        self._status_text = None
        self._refresh(layout=True, scroll=True)

    def _on_tool_progress(self, completed: int, total: int, stage: str | None = None) -> None:
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

    def _on_tool_end(self, tool_call_id: str, name: str, result_summary: str) -> None:
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

    def _on_text_delta(self, delta: str) -> None:
        self._raw_text += delta
        # Only display text after the --- separator
        if self._separator_seen:
            self._streaming_text += delta
        elif "---" in self._raw_text:
            self._separator_seen = True
            self._streaming_text = self._raw_text.split("---", 1)[1].lstrip("\n")
        else:
            return
        self._thinking_text = ""  # answer started — drop the reasoning trace
        self._status_text = None
        self._refresh(layout=True, scroll=True)

    def _on_thinking_delta(self, delta: str) -> None:
        # Surface the model's reasoning summary dim, until the answer prose begins.
        if self._separator_seen:
            return
        self._thinking_text += delta
        self._refresh(layout=True, scroll=True)

    def _on_usage(self, usage: Usage) -> None:
        self._usage = usage
        self._refresh()

    def _refresh(self, *, layout: bool = False, scroll: bool = False) -> None:
        try:
            self.refresh(layout=layout)
            if scroll:
                self.app.query_one("#chat-log").scroll_end(animate=False)
        except Exception:
            pass
