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
from textual.widget import Widget
from textual.widgets import Input, Static

from tabulaflow.app.display import DATA_PREVIEW_MAX_ROWS
from tabulaflow.app.theme import ACCENT, ACCENT_DIM, KEY_HINT, KEY_HINT_DIM, MESSAGE_SURFACE
from tabulaflow.app.screens import ChartBrowserScreen, DataBrowserScreen, QueryBrowserScreen
from tabulaflow.chat import (
    ChatEvent,
    ColumnsReturned,
    Failed,
    Finished,
    RowsReturned,
    TextDelta,
    ToolFinished,
    ToolOutcome,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)


if TYPE_CHECKING:
    import pandas as pd
    from rich.console import RenderableType

    from tabulaflow.chat import ChatResult
    from tabulaflow.app.display import RecordGroup, ViewItem
    from tabulaflow.core.types import Usage


# ---------------------------------------------------------------------------
# Autocomplete suggester
# ---------------------------------------------------------------------------

_SLASH_COMMANDS = sorted(["/help", "/exit", "/clear", "/connect", "/disconnect", "/model"])

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
        margin: 2 3;
    }
    """

    def __init__(self, *, model: str, reasoning_effort: str) -> None:
        super().__init__()
        self._model = model
        self._reasoning_effort = reasoning_effort

    def on_mount(self) -> None:
        from tabulaflow.app.banner import build_banner

        # Carve the wordmark's empty halves with this widget's *own* effective
        # background so they read as transparent against the chat log, whatever
        # the theme resolves it to.
        surface = self.background_colors[0].hex
        self.update(build_banner(model=self._model, reasoning_effort=self._reasoning_effort, surface=surface))


class UserMessage(Static):
    """Displays a user input message."""

    DEFAULT_CSS = f"""
    UserMessage {{
        margin: 1 2 1 0;
        padding: 0 1;
        border-left: heavy {ACCENT};
        background: {MESSAGE_SURFACE};
    }}
    """

    def __init__(self, text: str) -> None:
        super().__init__(Text(text))


class SystemMessage(Static):
    """Displays system/command output.

    Coerces a plain ``str`` to a Rich ``Text`` so markup is always parsed by Rich,
    never by Textual's own (differently-resolving) markup — keeping colors consistent
    with the rest of the app, which builds Rich renderables throughout."""

    DEFAULT_CSS = """
    SystemMessage {
        padding: 0 1;
    }
    """

    def __init__(self, content: "RenderableType") -> None:
        super().__init__(Text.from_markup(content) if isinstance(content, str) else content)


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


# Keys handled by the prefix/grouping logic or too noisy to show in a step label.
_NOISE_ARG_KEYS = frozenset({"db_alias", "refresh", "tab", "tool_call_id"})


def _fmt_arg_value(value: object, limit: int = 40) -> str:
    """Collapse whitespace and truncate a single arg value for a step label."""
    text = " ".join(str(value).split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def _summarize_generic_args(args: dict[str, object]) -> str:
    """Render arbitrary tool args as a clean label instead of a raw dict repr.

    Single meaningful arg → its bare value; multiple → ``key=value`` pairs. Drops
    empty values and noise keys so untreated tools degrade gracefully rather than
    dumping ``{'key': 'value', ...}``."""
    items = [(k, v) for k, v in args.items() if k not in _NOISE_ARG_KEYS and v not in (None, "", [], {})]
    if not items:
        return ""
    if len(items) == 1:
        return _fmt_arg_value(items[0][1])
    return ", ".join(f"{k}={_fmt_arg_value(v, 24)}" for k, v in items)[:80]


def summarize_tool_args(name: str, args: dict[str, object]) -> str:
    """Render a tool call's raw args as a compact one-line label for the TUI.

    Presentation lives here (the consumer), not in ``chat`` — the events carry the
    raw ``args`` dict and each frontend renders it as it likes. A handful of tools
    get bespoke labels; everything else falls back to a generic ``key=value``
    renderer. Truncates to keep the step line short."""
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
    if name == "browser_navigate":
        return _fmt_arg_value(args.get("url", ""), 60)
    return f"{db_prefix}{_summarize_generic_args(args)}"


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
        self._separator_seen = False
        self._status_text: str | None = "Thinking..."
        # Persistent spinner instances so animation state survives across renders.
        self._status_spinner = Spinner("dots", text=Text("Thinking...", style="dim"), style="dim")
        # Per-tool-call spinners so parallel running steps don't share a single
        # mutable spinner object (which would make every row display the same label).
        self._tool_spinners: dict[str, Spinner] = {}
        # Per-tool-call progress so concurrent fan-out tools don't overwrite each
        # other: tool_call_id -> (completed, total, stage, unit). total None means
        # an open-ended count.
        self._tool_progress: dict[str, tuple[int, int | None, str | None, str | None]] = {}
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

    # Event-stream consumption

    def apply(self, event: ChatEvent) -> None:
        """Dispatch one ``ChatEvent`` from ``ChatAgent.run_stream`` to the renderer.

        ``ThinkingDelta`` (model reasoning) is intentionally not rendered — the TUI
        shows the "Thinking..." spinner rather than streaming the reasoning text.
        Another frontend (e.g. a webapp) is free to render the trace from the same
        event; the choice of how to surface reasoning is the frontend's.
        """
        if isinstance(event, ToolStarted):
            self._on_tool_start(event.tool_call_id, event.name, summarize_tool_args(event.name, event.args))
        elif isinstance(event, ToolFinished):
            self._on_tool_end(event.tool_call_id, event.name, summarize_outcome(event.outcome))
        elif isinstance(event, ToolProgress):
            self._on_tool_progress(event.completed, event.total, event.stage, event.unit, event.tool_call_id)
        elif isinstance(event, TextDelta):
            self._on_text_delta(event.content)
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
        self._freeze_partial()

    def mark_failed(self) -> None:
        """Freeze the widget after an errored agent turn, preserving the tool steps
        rendered so far (the consumer calls this on a non-cancellation exception; no
        terminal ``Finished`` arrives). Mirrors ``mark_interrupted``."""
        self._freeze_partial()

    def _freeze_partial(self) -> None:
        """Freeze a partial run (interrupt or error): stop the timer, drop the live
        status spinner, and — when nothing was rendered — collapse out of the layout
        so the trailing status line sits flush against the user prompt."""
        self._status_text = None
        self._frozen = True
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
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

    @staticmethod
    def _format_progress(completed: int, total: int | None, stage: str | None, unit: str | None) -> str:
        """Format a progress counter: a ``completed/total`` fraction when ``total``
        is known, or a bare ``completed [unit]`` running count when it's ``None``.

        When ``stage`` is given it's prepended (e.g. ``resolve: 12/88``).
        """
        if total is None:
            body = f"{completed} {unit}" if unit else str(completed)
        else:
            body = f"{completed}/{total}"
        return f"{stage}: {body}" if stage else body

    def _find_running_step(self, tool_call_id: str | None) -> int | None:
        """Index of the running step for ``tool_call_id`` (the latest running step
        when ``tool_call_id`` is None), or ``None`` if there is no running step."""
        for i in range(len(self._steps) - 1, -1, -1):
            if self._steps[i][0] == "running" and (tool_call_id is None or self._steps[i][1] == tool_call_id):
                return i
        return None

    def _on_tool_progress(
        self,
        completed: int,
        total: int | None,
        stage: str | None = None,
        unit: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """Update the running tool step with a progress counter.

        ``total`` may be ``None`` for an open-ended running count (e.g. entities
        extracted so far), which renders as ``47 rows`` rather than a fraction.
        ``tool_call_id`` routes the tick to its own step so concurrent fan-out
        tools don't overwrite each other.
        """
        self._tool_progress[tool_call_id or ""] = (completed, total, stage, unit)
        suffix = self._format_progress(completed, total, stage, unit)
        i = self._find_running_step(tool_call_id)
        if i is not None:
            base_label = self._steps[i][3].split(" → ")[0]
            self._steps[i] = ("running", self._steps[i][1], self._steps[i][2], f"{base_label} → {suffix}")
        self._refresh(layout=True, scroll=True)

    def _on_tool_end(self, tool_call_id: str, name: str, result_summary: str) -> None:
        for i in range(len(self._steps) - 1, -1, -1):
            step = self._steps[i]
            if step[0] == "running" and step[1] == tool_call_id:
                label = step[3]
                progress = self._tool_progress.get(tool_call_id)
                if progress is not None:
                    base_label = label.split(" → ")[0]
                    completed, total, last_stage, unit = progress
                    # Open-ended count: the final tick already holds the total, so
                    # show it as-is. Fraction: pin to total/total to read "complete".
                    if total is None:
                        suffix = self._format_progress(completed, None, last_stage, unit)
                    else:
                        suffix = self._format_progress(total, total, last_stage, unit)
                    self._steps[i] = ("done", step[1], step[2], f"{base_label} → {suffix}")
                else:
                    self._steps[i] = ("done", step[1], step[2], f"{label} → {result_summary}")
                break
        self._tool_spinners.pop(tool_call_id, None)
        self._tool_progress.pop(tool_call_id, None)
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
        self._status_text = None
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
        margin: 1 2 0 1;
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
        from tabulaflow.app.display import build_result_views
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

        from tabulaflow.app.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

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
        from tabulaflow.app.display import VIEW_KIND_DATA

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
            from tabulaflow.app.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

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
        from tabulaflow.app.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

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
