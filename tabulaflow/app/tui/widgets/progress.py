"""Agent activity formatting and live progress widget."""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pathlib import Path
from rich.console import Group
from rich.spinner import Spinner
from rich.text import Text

from textual.timer import Timer
from textual.widget import Widget

from tabulaflow.app.tui.theme import (
    DIFF_ADDED,
    DIFF_REMOVED,
)
from tabulaflow.agents.chat import (
    AnswerDelta,
    ChatEvent,
    CompactionFinished,
    CompactionStarted,
    TurnFinished,
    ToolCallOutcome,
    ToolFinished,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)
from tabulaflow.app.tui.widgets.markdown import AgentTextBlock

if TYPE_CHECKING:
    from rich.console import RenderableType

    from tabulaflow.agents.chat import ChatResult
    from tabulaflow.agents.trace import Usage


_NOISE_ARG_KEYS = frozenset({"connector_alias", "refresh", "tab", "tool_call_id"})
_DIFFSTAT_TOKEN_RE = re.compile(r"(?<=\s)([+-]\d+)")
_UNLISTED_TOOL = "show_artifacts"
_BASH_COMMAND_PREVIEW_LIMIT = 180


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


def _summarize_edit_file(args: Mapping[str, object]) -> str:
    """A verb-led label for structured file editing."""
    command = str(args.get("command", ""))
    path = _fmt_path_value(args.get("path", "."), 48)
    if command == "replace":
        added, removed = _line_diffstat(str(args.get("old_text", "")), str(args.get("new_text", "")))
        return f"Edit {path}{_format_diffstat(added, removed)}"
    if command == "write":
        text = str(args.get("new_text", ""))
        added = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        return f"Write {path}{_format_diffstat(added, 0)}"
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


def _summarize_bash(args: Mapping[str, object]) -> str:
    command = str(args.get("command", ""))
    lines = [line for line in command.splitlines() if line.strip()]
    if not lines:
        return "Run"

    preview = _fmt_arg_value(command, _BASH_COMMAND_PREVIEW_LIMIT)
    line_count = f" ({len(lines)} lines)" if len(lines) > 1 else ""
    return f"Run {preview}{line_count}"


def summarize_tool_args(name: str, args: Mapping[str, object]) -> str:
    """Render a tool call as a compact, verb-led one-line label for the TUI.

    Every tool maps to ``<Verb> <target>`` — ``Query [main] SELECT …``,
    ``Inspect [main] orders``, ``Navigate stripe.com``, ``Edit foo.sql +5 -2`` — so
    the step list reads as a uniform action log. Presentation lives here (the
    consumer), not in ``chat``: events carry the raw ``args`` dict and each frontend
    renders it as it likes. Untreated / new tools fall back to a title-cased name
    plus a generic ``key=value`` summary. Truncates to keep the step line short."""
    connector_prefix = f"[{args['connector_alias']}] " if args.get("connector_alias") else ""

    if name == "run_query":
        query = " ".join(str(args.get("query", "")).split())
        if len(query) > 40:
            query = query[:37] + "..."
        return f"Query {connector_prefix}{query}"
    if name == "get_data_source_document":
        return f"Inspect {connector_prefix}".rstrip()
    if name == "get_table_schema":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        return f"Inspect {connector_prefix}{'.'.join(parts)}"
    if name == "get_column_json_schema":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        parts.append(str(args.get("column_name", "")))
        label = ".".join(parts)
        if args.get("path"):
            label += f", path={args['path']}"
        return f"Inspect {connector_prefix}{label}"
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
    if name == "write_result_table":
        source_id = str(args.get("source_id", ""))
        target_alias = str(args.get("target_alias", ""))
        target_schema = str(args.get("target_schema", "")) if args.get("target_schema") else ""
        target_table = str(args.get("target_table", ""))
        mode = str(args.get("mode", "create"))
        target = f"{target_schema}.{target_table}" if target_schema else target_table
        return f"Write {source_id} to [{target_alias}] {target} ({mode})"
    if name == "run_subagent_for_each_row":
        return f"Subagent {connector_prefix}{args.get('table_name', '')}"
    if name == "extract_rows_from_documents":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        return f"Extract {connector_prefix}{'.'.join(parts)}"
    if name == "add_canonical_name":
        parts = [str(args["schema_name"])] if args.get("schema_name") else []
        parts.append(str(args.get("table_name", "")))
        if args.get("input_column"):
            parts.append(str(args["input_column"]))
        return f"Canonicalize {connector_prefix}{'.'.join(parts)}"
    if name == "browser_navigate":
        return f"Navigate {_fmt_arg_value(args.get('url', ''), 60)}".rstrip()
    if name == "browser_screenshot":
        target = _fmt_arg_value(args.get("tab", ""))
        if args.get("ref"):
            target += f" {_fmt_arg_value(args['ref'])}"
        return f"Capture {target}".rstrip()
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
        return _summarize_bash(args)
    if name == "view":
        path = _fmt_path_value(args.get("path", "."), 48)
        return f"View {path}{_format_file_view_range(args.get('view_range'))}"
    if name == "edit_file":
        return _summarize_edit_file(args)
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

    File-edit git diffstat tokens keep their add/remove colors. That coloring is
    scoped to file mutation tools so arithmetic in a SQL snippet (``SELECT -1``) is never
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
    if not color_diffstat or name not in {"edit_file", "apply_patch"} or not _DIFFSTAT_TOKEN_RE.search(rest):
        text.append(rest, style="dim")
        return text

    for m in _DIFFSTAT_TOKEN_RE.finditer(rest):
        text.append(rest[pos : m.start()], style="dim")
        token = m.group(1)
        text.append(token, style=DIFF_ADDED if token.startswith("+") else DIFF_REMOVED)
        pos = m.end()
    text.append(rest[pos:], style="dim")
    return text


class AgentProgressWidget(Widget):
    """Shows agent execution progress with tool steps; streams the agent's text
    into sibling ``AgentTextBlock`` widgets.

    Driven by ``apply(event)`` over the ``ChatSession.run_stream`` event stream; the
    consumer (``TabulaflowApp._run_agent``) calls ``mark_interrupted`` on cancellation."""

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
        """Dispatch one ``ChatEvent`` from ``ChatSession.run_stream`` to the renderer.

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
        elif isinstance(event, CompactionStarted):
            self._status_text = "Compacting context..."
            self._refresh()
        elif isinstance(event, CompactionFinished):
            self._status_text = "Thinking..."
            self._refresh()
        elif isinstance(event, AnswerDelta):
            await self._on_answer_delta(event.content)
        elif isinstance(event, UsageUpdated):
            self._on_usage(event.usage)
        elif isinstance(event, TurnFinished):
            await self._on_finished(event.result)

    async def _on_finished(self, result: ChatResult) -> None:
        # Reconcile the live-streamed prose with the authoritative final text
        # (the terminal TurnFinished event carries the full ChatResult), then freeze.
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
        ``CancelledError``; no terminal ``TurnFinished`` arrives for an interrupt)."""
        if usage is not None:
            self._usage = usage
        self._interrupted = True
        await self._freeze_partial()

    async def mark_failed(self) -> None:
        """Freeze the widget after an errored agent turn, preserving the tool steps
        rendered so far (the consumer calls this on a non-cancellation exception; no
        terminal ``TurnFinished`` arrives). Mirrors ``mark_interrupted``."""
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
