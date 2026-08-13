"""Textual widgets for the tabulaflow TUI."""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypedDict

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from pathlib import Path
from rich.console import Group
from rich.spinner import Spinner
from rich.text import Text

from textual import events
from textual._compositor import Compositor
from textual.binding import Binding
from textual.content import Content, Span
from textual.geometry import Size
from textual.highlight import highlight
from textual.reactive import reactive
from textual.strip import Strip
from textual.suggester import Suggester
from textual.timer import Timer
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input, Markdown, Static
from textual.widgets._markdown import MarkdownFence, MarkdownTable, MarkdownTableContent

from tabulaflow.app.display import DATA_PREVIEW_MAX_ROWS
from tabulaflow.app.theme import (
    ACCENT,
    ACCENT_DIM,
    CODE_FUNCTION,
    CODE_TEXT,
    DIFF_ADDED,
    DIFF_REMOVED,
    KEY_HINT,
    KEY_HINT_DIM,
    MESSAGE_SURFACE,
    TabulaflowCodeHighlightTheme,
)
from tabulaflow.app.screens import ChartBrowserScreen, DataBrowserScreen, QueryBrowserScreen
from tabulaflow.chat import (
    AnswerDelta,
    ChatEvent,
    Finished,
    ToolCallOutcome,
    ToolFinished,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)


if TYPE_CHECKING:
    import pandas as pd
    from rich.console import RenderableType
    from textual.selection import Selection

    from tabulaflow.chat import ChatResult
    from tabulaflow.core.outputs import SelectionValue
    from tabulaflow.app.display import CardGroup, ViewItem
    from tabulaflow.core.types import Usage
    from tabulaflow.toolhub.output_store import OutputStore


class _MarkdownStream(Protocol):
    async def write(self, markdown_fragment: str) -> None: ...

    async def stop(self) -> None: ...


# ---------------------------------------------------------------------------
# Autocomplete suggester
# ---------------------------------------------------------------------------

_SLASH_COMMANDS = sorted(["/help", "/exit", "/clear", "/config", "/connect", "/disconnect"])

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


class BannerWidget(Widget):
    """Displays the welcome banner: the wordmark art above a text block.

    The two parts are separate widgets so the text block (version and starter
    examples) renders from a single ``Text`` and is therefore selectable, while
    the half-block art — which has no meaningful text to copy — is left as its
    own, non-selectable widget.
    """

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin: 2 3;
    }
    BannerWidget > Static {
        height: auto;
    }
    """

    def __init__(self, *, model: str | None, reasoning_effort: str | None) -> None:
        super().__init__()
        self._model = model
        self._reasoning_effort = reasoning_effort

    def compose(self) -> ComposeResult:
        from tabulaflow.app.banner import build_banner_text

        yield Static(classes="banner-art")
        yield Static(build_banner_text(model=self._model, reasoning_effort=self._reasoning_effort))

    def on_mount(self) -> None:
        from tabulaflow.app.banner import build_wordmark

        # Carve the wordmark's empty halves with the art widget's *own* effective
        # background so they read as transparent against the chat log, whatever
        # the theme resolves it to.
        art = self.query_one(".banner-art", Static)
        surface = art.background_colors[0].hex
        art.update(build_wordmark(surface))


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

# A git-style diffstat token (``+5`` / ``-2``) preceded by whitespace, so a path
# like ``model-2.sql`` is not mistaken for a removed-line count.
_DIFFSTAT_TOKEN_RE = re.compile(r"(?<=\s)([+-]\d+)")


def _fmt_arg_value(value: object, limit: int = 40) -> str:
    """Collapse whitespace and truncate a single arg value for a step label."""
    text = " ".join(str(value).split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def _truncate_middle(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 1:
        return "…"[:limit]
    head = max(1, (limit - 1) // 2)
    tail = limit - 1 - head
    return f"{text[:head]}…{text[-tail:]}" if tail else f"{text[:head]}…"


def _fmt_path_value(value: object, limit: int = 40) -> str:
    text = " ".join(str(value).split())
    path = Path(text)
    home = Path.home()
    if path.is_absolute():
        if path == home:
            text = "~"
        else:
            try:
                text = f"~/{path.relative_to(home)}"
            except ValueError:
                pass
    if len(text) <= limit:
        return text

    path = Path(text)
    filename = path.name
    if not filename:
        return _fmt_arg_value(text, limit)

    compact = f"{path.parent}/…/{filename}"
    if len(compact) <= limit:
        return compact

    suffix = f"…/{filename}"
    if len(suffix) <= limit:
        prefix_limit = limit - len(suffix)
        return f"{text[:prefix_limit]}{suffix}"

    filename_limit = max(0, limit - len("…/"))
    return f"…/{_truncate_middle(filename, filename_limit)}"


def _looks_like_local_path(value: object) -> bool:
    text = str(value).strip()
    if not text:
        return False
    if "://" in text:
        return False
    return text.startswith(("/", "~/", "./", "../")) or Path(text).suffix != ""


def _summarize_generic_args(args: Mapping[str, object]) -> str:
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


def _line_diffstat(old: str, new: str) -> tuple[int, int]:
    """Lines added/removed between two strings, git-diff style (changed lines only)."""
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    added = removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_lines, new_lines).get_opcodes():
        if tag == "replace":
            removed += i2 - i1
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "insert":
            added += j2 - j1
    return added, removed


def _format_diffstat(added: int, removed: int) -> str:
    parts = []
    if added:
        parts.append(f"+{added}")
    if removed:
        parts.append(f"-{removed}")
    return (" " + " ".join(parts)) if parts else ""


def _format_file_view_range(view_range: object) -> str:
    """Return a ``:start-end`` suffix for file view labels, or empty if unknown."""
    if not isinstance(view_range, list | tuple) or len(view_range) != 2:
        return ""

    start, end = view_range
    if type(start) is not int or type(end) is not int or start < 1:
        return ""
    if end < start:
        return ""
    if end == start:
        return f":{start}"
    return f":{start}-{end}"


def _summarize_file_editor(args: Mapping[str, object]) -> str:
    """A verb-led label for the file editor: ``Edit foo.sql +5 -2`` (git diffstat)."""
    command = str(args.get("command", ""))
    path = _fmt_path_value(args.get("path", "."), 48)
    if command == "str_replace":
        added, removed = _line_diffstat(str(args.get("old_str", "")), str(args.get("new_str", "")))
        return f"Edit {path}{_format_diffstat(added, removed)}"
    if command == "write_file":
        text = str(args.get("file_text", ""))
        added = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        return f"Write {path}{_format_diffstat(added, 0)}"
    if command == "view":
        return f"View {path}{_format_file_view_range(args.get('view_range'))}"
    return f"{command} {path}".strip()


@dataclass
class _PatchFileSummary:
    path: str
    added: int = 0
    removed: int = 0
    move: str = ""


def _summarize_apply_patch(args: Mapping[str, object]) -> str:
    patch = args.get("patch")
    if not isinstance(patch, str) or not patch:
        return "Edit"

    files: list[_PatchFileSummary] = []
    current: _PatchFileSummary | None = None
    in_body = False
    for line in patch.splitlines():
        if line.startswith("*** Add File: "):
            current = _PatchFileSummary(path=line.removeprefix("*** Add File: "))
            files.append(current)
            in_body = True
            continue
        if line.startswith("*** Update File: "):
            current = _PatchFileSummary(path=line.removeprefix("*** Update File: "))
            files.append(current)
            in_body = True
            continue
        if line.startswith("*** Delete File: "):
            current = _PatchFileSummary(path=line.removeprefix("*** Delete File: "))
            files.append(current)
            in_body = False
            continue
        if current is not None and line.startswith("*** Move to: "):
            current.move = line.removeprefix("*** Move to: ")
            continue
        if line.startswith("***"):
            in_body = False
            continue
        if current is None:
            continue
        if line.startswith("@@"):
            in_body = True
            continue
        if not in_body:
            continue
        if line.startswith("+"):
            current.added += 1
        elif line.startswith("-"):
            current.removed += 1

    if not files:
        return "Edit"

    total_added = sum(file.added for file in files)
    total_removed = sum(file.removed for file in files)
    if len(files) >= 2:
        return f"Edit {len(files)} files{_format_diffstat(total_added, total_removed)}"

    parts = []
    for file in files:
        path = _fmt_path_value(file.path, 36)
        move = file.move
        target = f"{path} -> {_fmt_path_value(move, 36)}" if move else path
        parts.append(f"{target}{_format_diffstat(file.added, file.removed)}")
    return "Edit " + ", ".join(parts)


def summarize_tool_args(name: str, args: Mapping[str, object]) -> str:
    """Render a tool call as a compact, verb-led one-line label for the TUI.

    Every tool maps to ``<Verb> <target>`` — ``Query [main] SELECT …``,
    ``Inspect [main] orders``, ``Navigate stripe.com``, ``Edit foo.sql +5 -2`` — so
    the step list reads as a uniform action log. Presentation lives here (the
    consumer), not in ``chat``: events carry the raw ``args`` dict and each frontend
    renders it as it likes. Untreated / new tools fall back to a title-cased name
    plus a generic ``key=value`` summary. Truncates to keep the step line short."""
    db_prefix = f"[{args['db_alias']}] " if args.get("db_alias") else ""

    if name == "run_query":
        query = " ".join(str(args.get("query", "")).split())
        if len(query) > 40:
            query = query[:37] + "..."
        return f"Query {db_prefix}{query}"
    if name == "get_db_document":
        return f"Inspect {db_prefix}".rstrip()
    if name == "get_table_schema":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        return f"Inspect {db_prefix}{'.'.join(parts)}"
    if name == "get_column_json_schema":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        parts.append(str(args.get("column_name", "")))
        label = ".".join(parts)
        if args.get("path"):
            label += f", path={args['path']}"
        return f"Inspect {db_prefix}{label}"
    if name == "render_chart":
        spec_str = args.get("vegalite_spec", "")
        try:
            spec = json.loads(spec_str) if isinstance(spec_str, str) else spec_str
            mark = spec.get("mark", "") if isinstance(spec, dict) else ""
            if isinstance(mark, dict):
                mark = mark.get("type", "")
            title = spec.get("title", "") if isinstance(spec, dict) else ""
            target = str(title) if title else str(mark)
        except (json.JSONDecodeError, TypeError):
            target = "chart"
        return f"Render Chart {target}".rstrip()
    if name == "render_map":
        spec_value = args.get("map_spec", {})
        try:
            spec = json.loads(spec_value) if isinstance(spec_value, str) else spec_value
            title = spec.get("title", "") if isinstance(spec, dict) else ""
            layers = spec.get("layers", []) if isinstance(spec, dict) else []
            if title:
                target = str(title)
            elif isinstance(layers, list) and len(layers) == 1 and isinstance(layers[0], dict):
                target = str(layers[0].get("type") or "map")
            else:
                target = "map"
        except (json.JSONDecodeError, TypeError):
            target = "map"
        return f"Render Map {target}".rstrip()
    if name == "render_graph":
        spec_value = args.get("graph_spec", {})
        try:
            spec = json.loads(spec_value) if isinstance(spec_value, str) else spec_value
            title = spec.get("title", "") if isinstance(spec, dict) else ""
            layout = spec.get("layout", "") if isinstance(spec, dict) else ""
            target = str(title or layout or "graph")
        except (json.JSONDecodeError, TypeError):
            target = "graph"
        return f"Render Graph {target}".rstrip()
    if name == "transfer_source_table":
        source_id = str(args.get("source_id", ""))
        target_alias = str(args.get("target_alias", ""))
        target_schema = str(args.get("target_schema", "")) if args.get("target_schema") else ""
        target_table = str(args.get("target_table", ""))
        mode = str(args.get("mode", "append"))
        target = f"{target_schema}.{target_table}" if target_schema else target_table
        return f"Transfer {source_id} to [{target_alias}] {target} ({mode})"
    if name == "run_subagent_for_each_row":
        return f"Subagent {db_prefix}{args.get('table_name', '')}"
    if name == "extract_rows_from_documents":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        return f"Extract {db_prefix}{'.'.join(parts)}"
    if name == "add_canonical_name":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        if args.get("input_column"):
            parts.append(str(args["input_column"]))
        return f"Canonicalize {db_prefix}{'.'.join(parts)}"
    if name == "browser_navigate":
        return f"Navigate {_fmt_arg_value(args.get('url', ''), 60)}".rstrip()
    if name == "browser_click":
        return f"Click {_fmt_arg_value(args.get('ref', ''))}".rstrip()
    if name == "browser_type":
        return f"Type {_fmt_arg_value(args.get('text', ''))}".rstrip()
    if name == "browser_scroll":
        return f"Scroll {args.get('direction', '')}".rstrip()
    if name == "browser_back":
        return "Back"
    if name == "browser_press":
        return f"Press {args.get('key', '')}".rstrip()
    if name == "browser_select":
        return f"Select {_fmt_arg_value(args.get('option', ''))}".rstrip()
    if name == "browser_wait":
        cond = args.get("text") or args.get("text_gone")
        target = _fmt_arg_value(cond) if cond else f"{args.get('seconds', '')}s"
        return f"Wait {target}".rstrip()
    if name == "connect_data_source":
        source = args.get("source", "")
        label = _fmt_path_value(source, 60) if _looks_like_local_path(source) else _fmt_arg_value(source, 60)
        return f"Connect {label}".rstrip()
    if name == "execute_bash":
        return f"Run {_fmt_arg_value(args.get('command', ''), 60)}".rstrip()
    if name == "file_editor":
        return _summarize_file_editor(args)
    if name == "apply_patch":
        return _summarize_apply_patch(args)
    return f"{name.replace('_', ' ').capitalize()} {_summarize_generic_args(args)}".rstrip()


def summarize_outcome(outcome: ToolCallOutcome | None) -> str:
    """A short outcome label for a finished tool step, or ``""`` when the outcome
    carries no extra information (a plain completion is already marked by the
    step's done-state, so it gets no suffix)."""
    if outcome is None:
        return ""
    if outcome.error:
        return "error"
    if outcome.count is None:
        return ""
    return f"{outcome.count} {outcome.unit}" if outcome.unit is not None else str(outcome.count)


def _styled_label(name: str, label: str, *, color_diffstat: bool = True) -> Text:
    """Render a step label with a bold-dim verb and dim details.

    File-editor git diffstat tokens keep their add/remove colors. That coloring is
    scoped to the file editor so arithmetic in a SQL snippet (``SELECT -1``) is never
    mistaken for a removed-line count. Tool failures are not reddened — the ``error``
    outcome stays dim like the rest of the label.
    """
    text = Text()
    verb_end = label.find(" ")
    if verb_end == -1:
        text.append(label, style="bold dim")
        return text

    text.append(label[:verb_end], style="bold dim")
    pos = 0
    rest = label[verb_end:]
    if not color_diffstat or name not in {"file_editor", "apply_patch"} or not _DIFFSTAT_TOKEN_RE.search(rest):
        text.append(rest, style="dim")
        return text

    for m in _DIFFSTAT_TOKEN_RE.finditer(rest):
        text.append(rest[pos : m.start()], style="dim")
        token = m.group(1)
        text.append(token, style=DIFF_ADDED if token.startswith("+") else DIFF_REMOVED)
        pos = m.end()
    text.append(rest[pos:], style="dim")
    return text


def _visible_text_for_inline_token(token: Token) -> str:
    """Plain text contribution of a markdown inline token."""
    if token.type == "text":
        return re.sub(r"\s+", " ", token.content)
    if token.type == "code_inline":
        return token.content
    if token.type == "hardbreak":
        return "\n"
    if token.type == "softbreak":
        return " "
    if token.children is None:
        return ""
    return "".join(_visible_text_for_inline_token(child) for child in token.children)


def _render_interactive_markdown_as_plain_text(markdown: MarkdownIt) -> None:
    """Render interactive markdown inline tokens as visible plain text.

    Textual attaches click metadata to markdown links and images, but terminal
    link support is inconsistent. Keep destinations copyable and terminal-
    detectable by removing interactive tokens and rendering explicit
    destinations as ``label (url)``. Autolinks and labels that already equal the
    destination render as just their visible label.
    """

    def replace_interactive_tokens(state: StateCore) -> None:
        for token in state.tokens:
            if token.type != "inline" or token.children is None:
                continue

            children: list[Token] = []
            in_link = False
            href = ""
            is_autolink = False
            label_parts: list[str] = []
            for child in token.children:
                if child.type == "link_open":
                    href = str(child.attrs.get("href", ""))
                    is_autolink = child.markup == "autolink" or child.info == "auto"
                    label_parts = []
                    in_link = True
                    continue

                if child.type == "image":
                    label = _visible_text_for_inline_token(child)
                    src = str(child.attrs.get("src", ""))
                    image_text = Token("text", "", 0)
                    image_text.content = label
                    if src and label != src:
                        image_text.content = f"{label} ({src})" if label else src
                    if in_link:
                        label_parts.append(image_text.content)
                    children.append(image_text)
                    continue

                if child.type == "link_close" and in_link:
                    label = "".join(label_parts)
                    if href and not is_autolink and label != href:
                        visible_destination = Token("text", "", 0)
                        visible_destination.content = f" ({href})"
                        children.append(visible_destination)
                    in_link = False
                    continue

                if in_link:
                    label_parts.append(_visible_text_for_inline_token(child))
                children.append(child)

            token.children = children

    markdown.core.ruler.after(
        "inline",
        "render_interactive_markdown_as_plain_text",
        replace_interactive_tokens,
    )


def _make_agent_markdown_parser() -> MarkdownIt:
    # Keep GFM-style strikethrough delimiters visible in the terminal instead of
    # emitting a Rich/Textual ``strike`` style. Terminal support for strikethrough
    # is inconsistent, so rendering ``~~text~~`` literally is more predictable in
    # the TUI.
    markdown = MarkdownIt("commonmark", {"html": False}).enable(["table"]).disable("hr")
    _render_interactive_markdown_as_plain_text(markdown)
    return markdown


class AgentMarkdownFence(MarkdownFence):
    @classmethod
    def highlight(cls, code: str, language: str, ansi: bool = False, dark: bool = False) -> Content:
        if ansi:
            return super().highlight(code, language, ansi=ansi, dark=dark)
        content = highlight(code, language=language or None, theme=TabulaflowCodeHighlightTheme)
        spans = [
            Span(span.start, span.end, CODE_TEXT) if str(span.style) == "$text" else span for span in content.spans
        ]
        return Content(content.plain, spans, content.cell_length, strip_control_codes=False)


class AgentMarkdownTableContent(MarkdownTableContent):
    """Markdown table content without per-cell hover tooltips."""

    def _clear_cell_tooltips(self) -> None:
        for cell in self.query(".cell, .header"):
            cell.tooltip = None

    def on_mount(self) -> None:
        super().on_mount()
        self._clear_cell_tooltips()

    def _update_content(self, headers: list[Content], rows: list[list[Content]]) -> None:
        super()._update_content(headers, rows)
        self._clear_cell_tooltips()

    async def _update_rows(self, updated_rows: list[list[Content]]) -> None:
        await super()._update_rows(updated_rows)
        self._clear_cell_tooltips()


class AgentMarkdownTable(MarkdownTable):
    def compose(self) -> ComposeResult:
        headers, rows = self._get_headers_and_rows()
        self._headers = headers
        self._rows = rows
        yield AgentMarkdownTableContent(headers, rows)


class AgentTextBlock(Markdown):
    """The agent's natural-language answer, streamed into its own widget.

    ``AgentProgressWidget`` mounts one as a sibling for the final answer;
    mid-turn narration arrives as a separate ``NarrationDelta`` the app doesn't
    handle, so it never reaches here.
    """

    BULLETS = ["- "]
    BLOCKS = {
        **Markdown.BLOCKS,
        "fence": AgentMarkdownFence,
        "code_block": AgentMarkdownFence,
        "table_open": AgentMarkdownTable,
    }

    DEFAULT_CSS = f"""
    AgentTextBlock {{
        padding: 0 1;
        margin: 1 0 0 0;
        height: auto;
    }}

    AgentTextBlock MarkdownHeader {{
        color: $foreground;
        margin: 1 0 1 0;
    }}

    AgentTextBlock MarkdownH1,
    AgentTextBlock MarkdownH2,
    AgentTextBlock MarkdownH3,
    AgentTextBlock MarkdownH4,
    AgentTextBlock MarkdownH5,
    AgentTextBlock MarkdownH6 {{
        background: transparent;
        color: $foreground;
        content-align: left middle;
        text-style: bold;
    }}

    AgentTextBlock MarkdownParagraph {{
        margin: 0 0 1 0;
    }}

    AgentTextBlock MarkdownBulletList Horizontal > Vertical > MarkdownParagraph,
    AgentTextBlock MarkdownOrderedList Horizontal > Vertical > MarkdownParagraph {{
        margin: 0;
    }}

    AgentTextBlock MarkdownBlockQuote {{
        background: transparent;
        border-left: vkey $foreground;
        margin: 1 0;
        padding: 0 1;
    }}

    AgentTextBlock MarkdownFence {{
        background: transparent;
        color: {CODE_TEXT};
        margin: 0 0 1 2;
        overflow: hidden hidden;
        padding: 0;
        scrollbar-size-horizontal: 0;
    }}

    AgentTextBlock MarkdownFence > Label {{
        padding: 0;
        text-wrap: wrap;
        width: 1fr;
    }}

    AgentTextBlock MarkdownBlock > .code_inline,
    AgentTextBlock MarkdownBlock:dark > .code_inline,
    AgentTextBlock MarkdownBlock:light > .code_inline {{
        background: transparent;
        color: {CODE_FUNCTION};
        text-style: none;
    }}

    AgentTextBlock MarkdownBullet,
    AgentTextBlock MarkdownTableContent > .header {{
        color: $foreground;
    }}

    AgentTextBlock MarkdownTableContent {{
        keyline: thin $foreground;
    }}

    AgentTextBlock MarkdownTableContent > .cell,
    AgentTextBlock MarkdownTableContent > .header {{
        padding: 0 1;
    }}
    """

    def __init__(self, markdown: str | None = None) -> None:
        super().__init__(markdown, parser_factory=_make_agent_markdown_parser, open_links=False)
        self._stream: _MarkdownStream | None = None

    async def write_delta(self, delta: str) -> None:
        if self._stream is None:
            self._stream = Markdown.get_stream(self)
        await self._stream.write(delta)

    async def replace_markdown(self, markdown: str) -> None:
        await self.stop_stream()
        await self.update(markdown)

    async def stop_stream(self) -> None:
        if self._stream is None:
            return
        stream = self._stream
        self._stream = None
        await stream.stop()

    async def freeze(self) -> "FrozenAgentTextBlock | None":
        """Replace the live Markdown widget tree with a lightweight snapshot.

        Textual's ``Markdown`` expands each completed answer into many mounted
        child widgets. Keeping all those old children live makes unrelated input
        updates slower as a conversation grows. Completed answers are static, so
        snapshot Textual's own rendered strips and replay them from a single
        widget without adding descendants to the Textual DOM.
        """
        await self.stop_stream()
        parent = self.parent
        if not isinstance(parent, Widget) or not self.is_mounted:
            return None
        children = self.walk_children(with_self=False)
        if children and not any(
            child.size.width > 0 and child.size.height > 0 for child in children if isinstance(child, Widget)
        ):
            self.refresh(layout=True)
            return None
        content_width = (
            self.size.width
            or self.content_size.width
            or self.container_size.width
            or parent.content_size.width
            or parent.size.width
            or self.app.size.width
        )
        if content_width <= 0:
            return None
        width = content_width + self.styles.gutter.width
        height = max(
            self.size.height,
            self.get_content_height(Size(content_width, self.app.size.height), self.app.size, content_width),
        )
        if height <= 0:
            return None
        compositor = Compositor()
        compositor.reflow(self, Size(width, height))
        strips = [Strip.join(list(line)) for line in compositor.render_full_update().strips]
        frozen = FrozenAgentTextBlock(strips, width)
        self.screen.clear_selection()
        with self.app.batch_update():
            await parent.mount(frozen, after=self)
            await self.remove()
        return frozen


def _strips_to_text(strips: list[Strip]) -> Text:
    """Convert pre-rendered strips into one styled, pre-line-broken text object."""
    out = Text(no_wrap=True, overflow="crop")
    for line_no, strip in enumerate(strips):
        if line_no:
            out.append("\n")
        remaining = len(strip.text.rstrip())
        for segment in strip._segments:
            if remaining <= 0:
                break
            text = segment.text[:remaining]
            out.append(text, segment.style)
            remaining -= len(text)
    return out


class FrozenAgentTextBlock(Static):
    """Lightweight snapshot of a completed assistant answer."""

    ALLOW_SELECT = True

    DEFAULT_CSS = """
    FrozenAgentTextBlock {
        margin: 1 0 0 0;
        height: auto;
    }
    """

    def __init__(self, strips: list[Strip], width: int) -> None:
        text = _strips_to_text(strips)
        super().__init__(text, markup=False)
        self._plain_text = text.plain
        self._width = width
        self._height = len(strips)

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return min(self._width, container.width) if container.width else self._width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return self._height

    def get_selection(self, selection: "Selection") -> tuple[str, str] | None:
        return selection.extract(self._plain_text), "\n"


_UNLISTED_TOOL = "show_artifacts"


class AgentProgressWidget(Widget):
    """Shows agent execution progress with tool steps; streams the agent's text
    into sibling ``AgentTextBlock`` widgets.

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
        # The final answer streams into this selectable sibling block. Mid-turn
        # narration arrives as ``NarrationDelta`` (not handled), so it never reaches
        # here — only the answer does.
        self._text_block: "AgentTextBlock | None" = None
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
        self._freeze_scheduled = False

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
                    line.append_text(_styled_label(_name, label, color_diffstat=False))
                    parts.append(line)
                else:
                    spinner = self._tool_spinners.get(tool_call_id)
                    if spinner is None:
                        spinner = Spinner("dots", style="dim")
                        self._tool_spinners[tool_call_id] = spinner
                    spinner.text = _styled_label(_name, label, color_diffstat=False)
                    parts.append(spinner)
            else:
                line = Text()
                line.append("→ ", style="dim")
                line.append_text(_styled_label(_name, label, color_diffstat=status == "done"))
                parts.append(line)

        if self._status_text and not has_running:
            if self._frozen:
                parts.append(Text(self._status_text, style="dim"))
            else:
                self._status_spinner.text = Text(self._status_text, style="dim")
                parts.append(self._status_spinner)

        return Group(*parts) if parts else Text()

    # Event-stream consumption

    async def apply(self, event: ChatEvent) -> None:
        """Dispatch one ``ChatEvent`` from ``ChatAgent.run_stream`` to the renderer.

        ``ThinkingDelta`` (model reasoning) is intentionally not rendered — the TUI
        shows the "Thinking..." spinner rather than streaming the reasoning text.
        Another frontend (e.g. a webapp) is free to render the trace from the same
        event; the choice of how to surface reasoning is the frontend's.
        """
        if isinstance(event, (ToolStarted, ToolFinished)) and event.name == _UNLISTED_TOOL:
            return  # declaring the turn's cards is bookkeeping, not a step worth showing
        if isinstance(event, ToolStarted):
            self._on_tool_start(event.tool_call_id, event.name, summarize_tool_args(event.name, event.args))
        elif isinstance(event, ToolFinished):
            self._on_tool_end(event.tool_call_id, event.name, summarize_outcome(event.outcome))
        elif isinstance(event, ToolProgress):
            self._on_tool_progress(event.completed, event.total, event.stage, event.unit, event.tool_call_id)
        elif isinstance(event, AnswerDelta):
            await self._on_answer_delta(event.content)
        elif isinstance(event, UsageUpdated):
            self._on_usage(event.usage)
        elif isinstance(event, Finished):
            await self._on_finished(event.result)

    async def _on_finished(self, result: ChatResult) -> None:
        # Reconcile the live-streamed prose with the authoritative final text
        # (the terminal Finished event carries the full ChatResult), then freeze.
        final_text = result.text or self._streaming_text
        if self._text_block is not None:
            if final_text:
                await self._text_block.replace_markdown(final_text)
            self._streaming_text = final_text
            await self._freeze_text_block()
        elif final_text:
            self._streaming_text = final_text
            await self._set_frozen_text(final_text)
        if result.usage is not None:
            self._usage = result.usage
        self._status_text = None
        self._frozen = True
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._refresh(layout=True)

    async def mark_interrupted(self, usage: Usage | None = None) -> None:
        """Freeze the widget after a cancelled run (the consumer calls this on
        ``CancelledError``; no terminal ``Finished`` arrives for an interrupt)."""
        if usage is not None:
            self._usage = usage
        self._interrupted = True
        await self._freeze_partial()

    async def mark_failed(self) -> None:
        """Freeze the widget after an errored agent turn, preserving the tool steps
        rendered so far (the consumer calls this on a non-cancellation exception; no
        terminal ``Finished`` arrives). Mirrors ``mark_interrupted``."""
        await self._freeze_partial()

    async def _freeze_partial(self) -> None:
        """Freeze a partial run (interrupt or error): stop the timer, drop the live
        status spinner, and — when nothing was rendered — collapse out of the layout
        so the trailing status line sits flush against the user prompt."""
        if self._text_block is not None:
            await self._text_block.stop_stream()
            await self._freeze_text_block_now()
        self._status_text = None
        self._frozen = True
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._refresh(layout=True)

    def _on_tool_start(self, tool_call_id: str, name: str, label: str) -> None:
        if self._status_text and self._status_text != "Thinking...":
            self._steps.append(("done", "", "__status__", self._status_text))
        self._steps.append(("running", tool_call_id, name, label or name))
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
                status = "failed" if result_summary == "error" else "done"
                progress = self._tool_progress.get(tool_call_id)
                if result_summary == "error":
                    base_label = label.split(" → ")[0]
                    self._steps[i] = (status, step[1], step[2], f"{base_label} → {result_summary}")
                elif progress is not None:
                    base_label = label.split(" → ")[0]
                    completed, total, last_stage, unit = progress
                    # Open-ended count: the final tick already holds the total, so
                    # show it as-is. Fraction: pin to total/total to read "complete".
                    if total is None:
                        suffix = self._format_progress(completed, None, last_stage, unit)
                    else:
                        suffix = self._format_progress(total, total, last_stage, unit)
                    self._steps[i] = (status, step[1], step[2], f"{base_label} → {suffix}")
                else:
                    # Append the outcome only when it carries display information;
                    # a plain completion gets no suffix.
                    new_label = f"{label} → {result_summary}" if result_summary else label
                    self._steps[i] = (status, step[1], step[2], new_label)
                break
        self._tool_spinners.pop(tool_call_id, None)
        self._tool_progress.pop(tool_call_id, None)
        self._status_text = "Thinking..."
        self._refresh(layout=True, scroll=True)

    async def _on_answer_delta(self, delta: str) -> None:
        # Only the final answer arrives as ``AnswerDelta`` (refs already stripped by
        # the chat layer); mid-turn ``NarrationDelta`` is not handled, so it's dropped.
        self._streaming_text += delta
        self._status_text = None
        await self._append_text(delta)
        self._refresh(layout=True, scroll=True)

    async def _append_text(self, delta: str) -> None:
        """Append ``delta`` to the answer block, mounting it as a sibling
        after the progress widget on first use."""
        block = await self._ensure_text_block()
        await block.write_delta(delta)

    async def _set_text(self, text: str) -> None:
        """Render ``text`` in the answer block, mounting it as a sibling
        after the progress widget on first use."""
        block = await self._ensure_text_block()
        await block.replace_markdown(text)

    async def _set_frozen_text(self, text: str) -> None:
        await self._set_text(text)
        await self._freeze_text_block()

    async def _freeze_text_block(self) -> None:
        if self._text_block is None:
            return
        if self._freeze_scheduled:
            return
        self._freeze_scheduled = True
        self.call_after_refresh(self._freeze_text_block_after_refresh)

    def _freeze_text_block_after_refresh(self) -> None:
        self.run_worker(self._freeze_text_block_now(), exclusive=True, group=f"freeze-answer-{id(self)}")

    async def _freeze_text_block_now(self) -> None:
        self._freeze_scheduled = False
        if self._text_block is not None and await self._text_block.freeze() is not None:
            self._text_block = None
            self._refresh(layout=True)

    async def _ensure_text_block(self) -> AgentTextBlock:
        if self._text_block is not None:
            return self._text_block
        self._text_block = AgentTextBlock()
        if isinstance(self.parent, Widget):
            await self.parent.mount(self._text_block, after=self)
        return self._text_block

    def _on_usage(self, usage: Usage) -> None:
        self._usage = usage
        self._refresh()

    def _refresh(self, *, layout: bool = False, scroll: bool = False) -> None:
        # Collapse when there's nothing to show (no tool steps, no status spinner)
        # — e.g. while a direct answer streams into its sibling text block. An
        # empty render still occupies a line and blocks margin-collapse between the
        # user message and the text block, which otherwise makes the text jump up
        # by two rows once the widget finally collapses on finish.
        self.display = bool(self._steps or self._status_text)
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
    Each record keeps its own selected view; stepping the view on one
    record never affects what another record shows.
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

    AgentResultWidget.-has-panel {
        padding: 0 1 1 1;
    }

    AgentResultWidget .top-bar-row {
        layout: horizontal;
        height: auto;
        margin: 0 0 1 0;
    }

    AgentResultWidget .card-bar {
        width: 1fr;
        height: auto;
        overflow-x: hidden;
        margin: 0 4 0 0;
    }

    AgentResultWidget .view-stepper {
        width: auto;
        height: auto;
    }

    AgentResultWidget .interpretation-panel {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 2;
        border: round #6a737d;
    }

    AgentResultWidget .interpretation-title {
        height: auto;
        margin: 0 0 1 0;
    }

    AgentResultWidget .interpretation-content {
        height: auto;
    }

    AgentResultWidget .bottom-hint {
        height: auto;
    }

    """

    current_card: reactive[int] = reactive(0, init=False)

    def __init__(
        self,
        result: ChatResult,
        cards: Sequence["CardGroup"],
        width: int = 80,
        output_store: "OutputStore | None" = None,
    ) -> None:
        super().__init__()
        self._result = result
        self._width = width
        self._choice_controls_cache = self._choice_controls_from_result(result)
        self._has_answer_controls = bool(self._choice_controls_cache)
        self.set_class(self._has_answer_controls, "-has-panel")
        self._applied_selection: dict[str, SelectionValue] = dict(result.output.default_selection)
        self._interpretation_cursor = 0
        self._cards = list(cards)
        # Selected view index per card; every card has at least one view.
        self._view_indices: list[int] = [0] * len(self._cards)
        self._output_store = output_store
        self._interpretation_title: Static | None = None
        self._interpretation_content: Static | None = None
        self._content = Static(id="result-content")
        self._mounted = False
        self._card_bar_widget: Static | None = None
        self._view_stepper_widget: Static | None = None
        self._bottom_hint_widget: Static | None = None
        # Record hit areas: (record_index, col_start, col_end, row) relative
        # to the record bar widget. Pills wrap across multiple rows when they
        # don't all fit on a single line.
        self._record_hit_areas: list[tuple[int, int, int, int]] = []
        # View hit areas: (target, col_start, col_end) relative to the view
        # stepper widget. Target is "prev" or "next".
        self._view_hit_areas: list[tuple[str, int, int]] = []
        # Interpretation choice hit areas: (flat_choice_index, row) relative to
        # the interpretation-content widget.
        self._choice_hit_areas: list[tuple[int, int]] = []

    @property
    def _has_top_bar(self) -> bool:
        """Top bar exists whenever the result has any displayable records."""
        return bool(self._cards)

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical

        if self._has_answer_controls:
            self._interpretation_title = Static(classes="interpretation-title")
            self._interpretation_content = Static(classes="interpretation-content")
            yield Vertical(
                self._interpretation_title,
                self._interpretation_content,
                classes="interpretation-panel",
            )
        if self._has_top_bar:
            self._card_bar_widget = Static(classes="card-bar")
            self._view_stepper_widget = Static(classes="view-stepper")
            yield Horizontal(
                self._card_bar_widget,
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
        # The first refresh can run before the child widgets have final widths;
        # refresh once more after layout so the interpretation header/separator
        # don't render with width 0 until the first keypress.
        self.call_after_refresh(self._refresh_all)

    def on_resize(self) -> None:
        if self._card_bar_widget is not None:
            self._update_card_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()

    def watch_current_card(self) -> None:
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
        if self._card_bar_widget is not None:
            self._update_card_bar()
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
        if self._has_answer_controls:
            self._update_interpretation_panel()
        self._update_content()
        if self._card_bar_widget is not None:
            self._update_card_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()
        if self._is_last_chat_item():
            chat_log = self.app.query_one("#chat-log")
            chat_log.scroll_end(animate=False)

    def _rebuild_cards_for_selection(self, cards: list["CardGroup"]) -> None:
        old_indices = self._view_indices
        old_card = self.current_card
        self._cards = cards
        self.current_card = min(old_card, max(len(self._cards) - 1, 0))
        self._view_indices = [0] * len(self._cards)
        for i, old in enumerate(old_indices[: len(self._cards)]):
            if self._cards[i].views:
                self._view_indices[i] = min(old, len(self._cards[i].views) - 1)

    async def _resolve_cards_for_selection(self, selection: dict[str, "SelectionValue"]) -> None:
        if self._output_store is None:
            return
        from tabulaflow.app.display import build_resolved_output_card_views
        from tabulaflow.toolhub.output_resolver import OutputResolver

        resolved_output = await OutputResolver(self._output_store).resolve(self._result.output, selection)
        cards = await build_resolved_output_card_views(resolved_output, self._output_store, self._width)
        self._rebuild_cards_for_selection(cards)
        self._refresh_all()

    def _is_last_chat_item(self) -> bool:
        """Return True when this widget is the last chat log child."""
        try:
            chat_log = self.app.query_one("#chat-log")
        except Exception:
            return False
        children = list(chat_log.children)
        return bool(children) and children[-1] is self

    def _current_record_or_none(self) -> "CardGroup | None":
        if not self._cards:
            return None
        idx = min(self.current_card, len(self._cards) - 1)
        return self._cards[idx]

    def _current_view_or_none(self) -> "ViewItem | None":
        rec = self._current_record_or_none()
        if rec is None or not rec.views:
            return None
        return rec.views[self._view_indices[min(self.current_card, len(self._cards) - 1)]]

    @staticmethod
    def _choice_controls_from_result(result: "ChatResult") -> list[Any]:
        from tabulaflow.core.outputs import ChoiceParameter

        return [parameter for parameter in result.output.parameters if isinstance(parameter, ChoiceParameter)]

    def _choice_controls(self) -> list[Any]:
        return self._choice_controls_cache

    def _choice_count(self) -> int:
        return sum(len(control.choices) for control in self._choice_controls())

    def _cursor_location(self) -> tuple[int, int]:
        controls = self._choice_controls()
        assert controls
        cursor = self._interpretation_cursor
        for control_idx, control in enumerate(controls):
            if cursor < len(control.choices):
                return control_idx, cursor
            cursor -= len(control.choices)
        last_control = len(controls) - 1
        return last_control, len(controls[last_control].choices) - 1

    def _choice_flat_index(self, control_idx: int, choice_idx: int) -> int:
        controls = self._choice_controls()
        return sum(len(control.choices) for control in controls[:control_idx]) + choice_idx

    def _move_interpretation_cursor(self, delta: int) -> None:
        max_cursor = self._choice_count() - 1
        if max_cursor < 0:
            return
        self._interpretation_cursor = max(0, min(max_cursor, self._interpretation_cursor + delta))
        self._refresh_all()

    def _apply_interpretation_cursor(self) -> None:
        controls = self._choice_controls()
        if not controls:
            return
        control_idx, choice_idx = self._cursor_location()
        control = controls[control_idx]
        choice = control.choices[choice_idx]
        if self._applied_selection.get(control.id) == choice.id:
            return
        self._applied_selection = {**self._applied_selection, control.id: choice.id}
        if self._output_store is not None:
            self.run_worker(self._resolve_cards_for_selection(dict(self._applied_selection)), exclusive=True)
        else:
            self._refresh_all()

    def _update_interpretation_panel(self) -> None:
        from rich.style import Style

        if not self._has_answer_controls:
            return
        if self._interpretation_title is None or self._interpretation_content is None:
            return

        available = self._interpretation_title.size.width or 80
        hint = Text(no_wrap=True)
        hint.append("↑↓", style=self._focus_key_hint)
        hint.append(" Move · ", style="dim")
        hint.append("Space", style=self._focus_key_hint)
        hint.append(" Apply", style="dim")
        title = Text("Refine interpretation", style="bold dim")
        title_line = Text(no_wrap=True, overflow="crop")
        title_line.append_text(title)
        title_line.append(" " * max(1, available - title.cell_len - hint.cell_len))
        title_line.append_text(hint)
        self._interpretation_title.update(title_line)

        controls = self._choice_controls()
        rows: list[Text] = []
        self._choice_hit_areas = []
        if not controls:
            self._interpretation_content.update(Text("No supported answer controls yet.", style="dim"))
            return
        cursor_control, cursor_choice = self._cursor_location()
        row = 0
        for control_idx, control in enumerate(controls):
            if rows:
                rows.append(Text(""))
                row += 1
            rows.append(Text(control.label, style=Style(bold=True)))
            row += 1
            for choice_idx, choice in enumerate(control.choices):
                is_cursor = control_idx == cursor_control and choice_idx == cursor_choice
                is_applied = self._applied_selection.get(control.id) == choice.id
                line = Text()
                line.append("  ")
                line.append(
                    "❯ " if is_cursor else "  ",
                    style=KEY_HINT if is_cursor and self.has_focus else KEY_HINT_DIM if is_cursor else "",
                )
                line.append("● " if is_applied else "  ", style=self._focus_accent if is_applied else "")
                if is_applied:
                    label_style = Style(bold=True, color=self._focus_accent)
                elif is_cursor:
                    label_style = Style(bold=True)
                else:
                    label_style = Style()
                line.append(choice.label, style=label_style)
                rows.append(line)
                self._choice_hit_areas.append((self._choice_flat_index(control_idx, choice_idx), row))
                row += 1
        self._interpretation_content.update(Text("\n").join(rows))

    def _update_card_bar(self) -> None:
        """Render record pills left-anchored, wrapping across multiple lines.

        All pills are shown; when the row fills, subsequent pills wrap to a
        new line. When more than one record exists, a ``·  ←/→ Switch record``
        hint is appended inline after the final pill if it fits on the last
        line, otherwise on a new line below.

        Hit areas are stored as ``(record_index, col_start, col_end, row)``
        relative to ``self._card_bar_widget`` so the click handler can test
        ``event.x``/``event.y`` directly without worrying about the enclosing
        layout.
        """
        from rich.style import Style

        if self._card_bar_widget is None:
            return

        available_width = self._card_bar_widget.size.width or 80
        card_interactive = len(self._cards) > 1

        HINT_SEP = " · "
        HINT_KEY = "←/→"
        HINT_TEXT = " Switch record"
        hint_width = len(HINT_SEP) + len(HINT_KEY) + len(HINT_TEXT) if card_interactive else 0

        SEP = 1  # space between pills on the same row
        dim_style = Style(dim=True)

        line = Text(no_wrap=True, overflow="crop")
        self._record_hit_areas = []
        row = 0
        col = 0

        for rec_idx, r in enumerate(self._cards):
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
                if rec_idx == self.current_card
                else Style(dim=True)
            )
            line.append_text(Text(pill, style=pill_style))
            col += pill_width
            self._record_hit_areas.append((rec_idx, col_start, col, row))

        if card_interactive:
            if col + hint_width > available_width:
                line.append("\n")
            line.append_text(Text(HINT_SEP, style=dim_style))
            line.append_text(Text("←", style=self._focus_key_hint))
            line.append_text(Text("/", style="dim"))
            line.append_text(Text("→", style=self._focus_key_hint))
            line.append_text(Text(HINT_TEXT, style="dim"))

        self._card_bar_widget.update(line)

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

        cur_view = self._current_view_or_none()
        assert cur_view is not None
        cur_kind = cur_view.kind
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
        if not self._has_answer_controls:
            # ↑↓ and Enter only do anything when this widget is focused, so
            # both follow focus-state dimming (bright when focused, dim when
            # not) — the "way in" comes from the docked bottom-bar hint, not
            # from the widget itself.
            hint.append("↑↓", style=self._focus_key_hint)
            hint.append(" Prev/Next result    ", style="dim")
            hint.append("↵", style=self._focus_key_hint)
            hint.append(" Inspect", style="dim")
        else:
            hint.append("↵", style=self._focus_key_hint)
            hint.append(" Inspect    ", style="dim")
            hint.append("Esc", style=self._focus_key_hint)
            hint.append(" Back to input", style="dim")

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

        if self._interpretation_content is not None and event.widget is self._interpretation_content:
            for flat_idx, row in self._choice_hit_areas:
                if row == event.y:
                    self._interpretation_cursor = flat_idx
                    self._apply_interpretation_cursor()
                    return
            return

        if self._card_bar_widget is not None and event.widget is self._card_bar_widget:
            for rec_idx, col_start, col_end, row in self._record_hit_areas:
                if row == event.y and col_start <= event.x < col_end:
                    self.current_card = rec_idx
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

    def _step_view(self, delta: int) -> None:
        rec = self._current_record_or_none()
        if rec is not None and len(rec.views) > 1:
            self._view_indices[self.current_card] = (self._view_indices[self.current_card] + delta) % len(rec.views)
            self._refresh_all()

    def action_next_view(self) -> None:
        self._step_view(1)

    def action_prev_view(self) -> None:
        self._step_view(-1)

    def action_next_record(self) -> None:
        if len(self._cards) > 1:
            self.current_card = (self.current_card + 1) % len(self._cards)

    def action_prev_record(self) -> None:
        if len(self._cards) > 1:
            self.current_card = (self.current_card - 1) % len(self._cards)

    def action_result_enter(self) -> None:
        self.run_worker(self.action_open_full_screen(), exclusive=True)

    def action_apply_interpretation(self) -> None:
        if self._has_answer_controls:
            self._apply_interpretation_cursor()

    def action_result_up(self) -> None:
        if self._has_answer_controls:
            self._move_interpretation_cursor(-1)
        else:
            self.action_focus_prev_result()

    def action_result_down(self) -> None:
        if self._has_answer_controls:
            self._move_interpretation_cursor(1)
        else:
            self.action_focus_next_result()

    can_focus = True

    BINDINGS = [
        ("right_square_bracket", "next_view", "Next view"),
        ("left_square_bracket", "prev_view", "Previous view"),
        ("right", "next_record", "Next record"),
        ("left", "prev_record", "Previous record"),
        ("space", "apply_interpretation", "Apply interpretation"),
        ("enter", "result_enter", "Full screen"),
        # ``priority=True`` so these beat ``VerticalScroll``'s own priority
        # up/down bindings (which would otherwise scroll the chat log
        # instead of moving between focused result widgets).
        Binding("up", "result_up", "Move up", priority=True),
        Binding("down", "result_down", "Move down", priority=True),
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
            df = await self._fetch_df(rec.source_result_id)
            if df is not None:
                self.app.push_screen(ChartBrowserScreen(title=title, df=df, vegalite_spec=view.chart_spec))
            return
        if view.kind == VIEW_KIND_DATA:
            df = await self._fetch_df(rec.source_result_id)
            if df is not None:
                self.app.push_screen(DataBrowserScreen(title=title, df=df))
            return
        if view.kind == VIEW_KIND_QUERY and view.query is not None:
            query, lexer = view.query
            self.app.push_screen(QueryBrowserScreen(title=title, query=query, lexer=lexer))

    async def _fetch_df(self, result_id: str | None) -> pd.DataFrame | None:
        """Fetch a DataFrame from OutputStore, loading from DuckDB if needed."""
        if self._output_store is None or result_id is None:
            return None
        try:
            payload = await self._output_store.get_payload(result_id)
            return payload.df
        except (KeyError, ValueError):
            return None


# ---------------------------------------------------------------------------
# Schema browser screen
# ---------------------------------------------------------------------------
