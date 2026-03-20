"""File editor tool for dbt agents.

Provides ``view``, ``create``, and ``str_replace`` commands scoped to a
working directory.  Paths are always relative to the working directory and
validated to prevent directory traversal.

Adapted from the Anthropic/OpenHands ``str_replace_editor`` pattern.
"""

import os
import re
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel
from pydantic_ai import Tool


SNIPPET_CONTEXT_LINES = 4
MAX_RESPONSE_LINES = 500


class FileEditorToolMetrics(BaseModel):
    num_view: int = 0
    num_create: int = 0
    num_str_replace: int = 0
    error_count: int = 0


class FileEditorTool:
    """File editor with ``view``, ``create``, and ``str_replace`` commands.

    All *path* arguments are relative to ``working_dir``.  Absolute paths and
    paths that escape the working directory (e.g. ``../../etc/passwd``) are
    rejected.
    """

    name: ClassVar = "file_editor"

    def __init__(self, working_dir: str) -> None:
        self._working_dir = Path(working_dir).resolve()
        if not self._working_dir.is_dir():
            raise ValueError(f"working_dir is not a directory: {working_dir}")
        self._metrics = FileEditorToolMetrics()

    def _resolve(self, path: str) -> Path:
        """Resolve a relative path against working_dir and validate it."""
        p = Path(path)
        if p.is_absolute():
            raise ValueError(
                f"Path must be relative to the working directory, got absolute path: {path}"
            )
        resolved = (self._working_dir / p).resolve()
        if not str(resolved).startswith(str(self._working_dir)):
            raise ValueError(f"Path escapes the working directory: {path}")
        return resolved

    def _make_numbered(self, content: str, start_line: int = 1) -> str:
        """Add line numbers to content."""
        lines = content.split("\n")
        return "\n".join(f"{i + start_line:6}\t{line}" for i, line in enumerate(lines))

    # -- commands -------------------------------------------------------------

    def _view(self, resolved: Path, path: str, view_range: list[int] | None) -> str:
        if resolved.is_dir():
            if view_range:
                return "Error: view_range is not supported for directories."
            entries: list[str] = []
            for root, dirs, files in os.walk(resolved):
                depth = str(root).replace(str(resolved), "").count(os.sep)
                if depth >= 2:
                    dirs.clear()
                    continue
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                rel = os.path.relpath(root, self._working_dir)
                if rel == ".":
                    rel = ""
                for d in sorted(dirs):
                    entries.append(os.path.join(rel, d) + "/")
                for f in sorted(files):
                    if not f.startswith("."):
                        entries.append(os.path.join(rel, f))
            return f"Directory listing of {path or '.'}:\n" + "\n".join(entries)

        if not resolved.is_file():
            return f"Error: {path} does not exist."

        content = resolved.read_text()
        num_lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

        if not view_range:
            if num_lines > MAX_RESPONSE_LINES:
                content = "\n".join(content.split("\n")[:MAX_RESPONSE_LINES])
                return (
                    self._make_numbered(content)
                    + f"\n\n(showing first {MAX_RESPONSE_LINES} of {num_lines} lines)"
                )
            return self._make_numbered(content)

        if len(view_range) != 2:
            return "Error: view_range must be a list of two integers [start, end]."
        start, end = view_range
        if start < 1:
            return f"Error: start line must be >= 1, got {start}."
        if end == -1:
            end = num_lines
        if end < start:
            return f"Error: end line ({end}) must be >= start line ({start})."

        lines = content.split("\n")
        selected = lines[start - 1 : end]
        return self._make_numbered("\n".join(selected), start_line=start)

    def _create(self, resolved: Path, path: str, file_text: str) -> str:
        if resolved.exists():
            return f"Error: {path} already exists. Use str_replace to edit it."
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(file_text)
        return f"File created: {path} ({file_text.count(chr(10)) + 1} lines)"

    def _str_replace(self, resolved: Path, path: str, old_str: str, new_str: str) -> str:
        if not resolved.is_file():
            return f"Error: {path} does not exist."
        if old_str == new_str:
            return "Error: old_str and new_str are identical."

        content = resolved.read_text()
        pattern = re.escape(old_str)
        matches = list(re.finditer(pattern, content))

        if not matches:
            stripped_old = old_str.strip()
            stripped_new = new_str.strip()
            pattern = re.escape(stripped_old)
            matches = list(re.finditer(pattern, content))
            if not matches:
                return f"Error: old_str not found in {path}."
            old_str, new_str = stripped_old, stripped_new

        if len(matches) > 1:
            line_numbers = sorted(
                set(content.count("\n", 0, m.start()) + 1 for m in matches)
            )
            return (
                f"Error: old_str found {len(matches)} times in {path} "
                f"(lines {line_numbers}). It must be unique — include more context."
            )

        match = matches[0]
        new_content = content[: match.start()] + new_str + content[match.end() :]
        resolved.write_text(new_content)

        replacement_line = content.count("\n", 0, match.start()) + 1
        start = max(1, replacement_line - SNIPPET_CONTEXT_LINES)
        end = replacement_line + SNIPPET_CONTEXT_LINES + new_str.count("\n")
        snippet_lines = new_content.split("\n")[start - 1 : end]
        snippet = self._make_numbered("\n".join(snippet_lines), start_line=start)

        return f"Edited {path}. Snippet:\n{snippet}"

    # -- main entry point -----------------------------------------------------

    async def __call__(
        self,
        command: Literal["view", "create", "str_replace"],
        path: str = ".",
        file_text: str | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        view_range: list[int] | None = None,
    ) -> str:
        """Edit files in the dbt project directory.

        Commands:
        - ``view``: View a file (with optional line range) or list a directory.
        - ``create``: Create a new file (fails if it already exists).
        - ``str_replace``: Replace an exact string in a file. ``old_str`` must
          match exactly one location.

        All paths are relative to the project working directory.

        Args:
            command: One of ``"view"``, ``"create"``, ``"str_replace"``.
            path: Relative path to the file or directory.
            file_text: Content for ``create`` command.
            old_str: String to find for ``str_replace``.
            new_str: Replacement string for ``str_replace``.
            view_range: Optional ``[start_line, end_line]`` for ``view`` (1-indexed, end=-1 means EOF).
        """
        try:
            resolved = self._resolve(path)
        except ValueError as e:
            self._metrics.error_count += 1
            return f"Error: {e}"

        if command == "view":
            self._metrics.num_view += 1
            return self._view(resolved, path, view_range)
        elif command == "create":
            self._metrics.num_create += 1
            if file_text is None:
                self._metrics.error_count += 1
                return "Error: file_text is required for the create command."
            return self._create(resolved, path, file_text)
        elif command == "str_replace":
            self._metrics.num_str_replace += 1
            if old_str is None:
                self._metrics.error_count += 1
                return "Error: old_str is required for the str_replace command."
            if new_str is None:
                self._metrics.error_count += 1
                return "Error: new_str is required for the str_replace command."
            return self._str_replace(resolved, path, old_str, new_str)
        else:
            self._metrics.error_count += 1
            return f"Error: unknown command '{command}'. Use view, create, or str_replace."

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> FileEditorToolMetrics:
        return self._metrics
