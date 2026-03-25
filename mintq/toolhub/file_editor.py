"""File editor tool for dbt agents.

Provides ``view``, ``write_file``, and ``str_replace`` commands scoped to a
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
MAX_RESPONSE_LINES = 200
MAX_RESPONSE_CHARS = 40000
MAX_DIR_ENTRIES = 200


class FileEditorToolMetrics(BaseModel):
    num_view: int = 0
    num_write_file: int = 0
    num_str_replace: int = 0
    error_count: int = 0


class FileEditorTool:
    """File editor with ``view``, ``write_file``, and ``str_replace`` commands.

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
            raise ValueError(f"Path must be relative to the working directory, got absolute path: {path}")
        resolved = (self._working_dir / p).resolve()
        if not str(resolved).startswith(str(self._working_dir)):
            raise ValueError(f"Path escapes the working directory: {path}")
        return resolved

    @staticmethod
    def _truncate_line(line: str, max_chars: int) -> str:
        """Truncate a single line using head...tail if it exceeds *max_chars*."""
        if len(line) <= max_chars:
            return line
        half = max_chars // 2
        if half == 0:
            return f"...({len(line)} chars)..."
        return line[:half] + f"...({len(line)} chars)..." + line[-half:]

    def _make_numbered(
        self,
        content: str,
        start_line: int = 1,
        max_line_chars: int | None = None,
    ) -> str:
        """Add line numbers to content, optionally truncating long lines."""
        lines = content.split("\n")
        if max_line_chars is not None:
            lines = [self._truncate_line(line, max_line_chars) for line in lines]
        return "\n".join(f"{i + start_line:6}\t{line}" for i, line in enumerate(lines))

    # -- commands -------------------------------------------------------------

    def _error(self, msg: str) -> str:
        self._metrics.error_count += 1
        return f"(error: {msg})"

    def _parse_range(self, view_range: list[int] | None, total: int) -> tuple[int, int] | str:
        """Parse and validate a 1-indexed [start, end] range.

        Returns (start, end) as 0-indexed inclusive bounds, or an error string.
        """
        if not view_range:
            return (0, total - 1)
        if len(view_range) != 2:
            return self._error("view_range must be a list of two integers [start, end].")
        start, end = view_range
        if start < 1:
            return self._error(f"start must be >= 1, got {start}.")
        if end == -1:
            end = total
        if end < start:
            return self._error(f"end ({end}) must be >= start ({start}).")
        return (start - 1, end - 1)

    def _view_dir(self, resolved: Path, path: str, view_range: list[int] | None) -> str:
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

        total = len(entries)
        result = self._parse_range(view_range, total)
        if isinstance(result, str):
            return result
        lo, hi = result

        selected = entries[lo : hi + 1]
        label = path or "."
        if view_range:
            header = f"Directory listing of {label} (entries {lo + 1}-{min(hi + 1, total)} of {total}):\n"
        elif total > MAX_DIR_ENTRIES:
            selected = entries[:MAX_DIR_ENTRIES]
            header = f"Directory listing of {label}:\n"
            return header + "\n".join(selected) + f"\n\n(showing first {MAX_DIR_ENTRIES} of {total} entries)"
        else:
            header = f"Directory listing of {label}:\n"
        return header + "\n".join(selected)

    def _view_file(self, resolved: Path, path: str, view_range: list[int] | None) -> str:
        try:
            content = resolved.read_text()
        except (UnicodeDecodeError, ValueError):
            return self._error(f"{path} is a binary file and cannot be displayed.")

        lines = content.split("\n")
        num_lines = len(lines) - (1 if content.endswith("\n") else 0)
        header = f"File: {path}\n"

        result = self._parse_range(view_range, num_lines)
        if isinstance(result, str):
            return result
        lo, hi = result

        if not view_range and num_lines > MAX_RESPONSE_LINES:
            selected = lines[:MAX_RESPONSE_LINES]
            per_line = MAX_RESPONSE_CHARS // max(len(selected), 1)
            numbered = self._make_numbered("\n".join(selected), max_line_chars=per_line)
            return header + numbered + f"\n\n(showing first {MAX_RESPONSE_LINES} of {num_lines} lines)"

        selected = lines[lo : hi + 1]
        truncated = False
        if len(selected) > MAX_RESPONSE_LINES:
            selected = selected[:MAX_RESPONSE_LINES]
            truncated = True
        per_line = MAX_RESPONSE_CHARS // max(len(selected), 1)
        numbered = self._make_numbered("\n".join(selected), start_line=lo + 1, max_line_chars=per_line)
        if truncated:
            return header + numbered + f"\n\n(showing {MAX_RESPONSE_LINES} of {hi - lo + 1} lines in range)"
        return header + numbered

    def _view(self, resolved: Path, path: str, view_range: list[int] | None) -> str:
        if resolved.is_dir():
            return self._view_dir(resolved, path, view_range)
        if not resolved.is_file():
            return self._error(f"{path} does not exist.")
        return self._view_file(resolved, path, view_range)

    def _write_file(self, resolved: Path, path: str, file_text: str) -> str:
        is_new = not resolved.exists()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(file_text)
        num_lines = file_text.count("\n") + (1 if file_text and not file_text.endswith("\n") else 0)
        action = "Created" if is_new else "Wrote"
        return f"{action}: {path} ({num_lines} lines)"

    def _str_replace(self, resolved: Path, path: str, old_str: str, new_str: str) -> str:
        if not resolved.is_file():
            return self._error(f"{path} does not exist.")
        if old_str == new_str:
            return self._error("old_str and new_str are identical.")

        try:
            content = resolved.read_text()
        except (UnicodeDecodeError, ValueError):
            return self._error(f"{path} is a binary file and cannot be edited.")
        pattern = re.escape(old_str)
        matches = list(re.finditer(pattern, content))

        if not matches:
            stripped_old = old_str.strip()
            stripped_new = new_str.strip()
            pattern = re.escape(stripped_old)
            matches = list(re.finditer(pattern, content))
            if not matches:
                return self._error(f"old_str not found in {path}.")
            old_str, new_str = stripped_old, stripped_new

        if len(matches) > 1:
            line_numbers = sorted(set(content.count("\n", 0, m.start()) + 1 for m in matches))
            return self._error(
                f"old_str found {len(matches)} times in {path} "
                f"(lines {line_numbers}). It must be unique — include more context."
            )

        match = matches[0]
        new_content = content[: match.start()] + new_str + content[match.end() :]
        resolved.write_text(new_content)

        replacement_line = content.count("\n", 0, match.start()) + 1
        start = max(1, replacement_line - SNIPPET_CONTEXT_LINES)
        end = replacement_line + SNIPPET_CONTEXT_LINES + new_str.count("\n")
        snippet_lines = new_content.split("\n")[start - 1 : end]
        per_line = MAX_RESPONSE_CHARS // max(len(snippet_lines), 1)
        snippet = self._make_numbered("\n".join(snippet_lines), start_line=start, max_line_chars=per_line)

        return f"Edited {path}. Snippet:\n{snippet}"

    # -- main entry point -----------------------------------------------------

    async def __call__(
        self,
        command: Literal["view", "write_file", "str_replace"],
        path: str = ".",
        file_text: str | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        view_range: list[int] | None = None,
    ) -> str:
        """Edit files in the dbt project directory.

        Commands:
        - ``view``: View a file (with optional line range) or list a directory (up to 2 levels deep).
        - ``write_file``: Create or overwrite a file with the given content.
        - ``str_replace``: Replace an exact string in a file. ``old_str`` must
          match exactly one location.

        All paths are relative to the project working directory.

        Args:
            command: One of ``"view"``, ``"write_file"``, ``"str_replace"``.
            path: Relative path to the file or directory.
            file_text: Content for ``write_file`` command.
            old_str: String to find for ``str_replace``.
            new_str: Replacement string for ``str_replace``.
            view_range: Optional ``[start, end]`` for ``view`` (1-indexed,
                end=-1 means last). For files, selects a line range; for
                directories, selects an entry range for pagination.
        """
        try:
            resolved = self._resolve(path)
        except ValueError as e:
            return self._error(str(e))

        if command == "view":
            self._metrics.num_view += 1
            return self._view(resolved, path, view_range)
        elif command == "write_file":
            if file_text is None:
                return self._error("file_text is required for the write_file command.")
            self._metrics.num_write_file += 1
            return self._write_file(resolved, path, file_text)
        elif command == "str_replace":
            if old_str is None:
                return self._error("old_str is required for the str_replace command.")
            if new_str is None:
                return self._error("new_str is required for the str_replace command.")
            self._metrics.num_str_replace += 1
            return self._str_replace(resolved, path, old_str, new_str)
        else:
            return self._error(f"unknown command '{command}'. Use view, write_file, or str_replace.")

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> FileEditorToolMetrics:
        return self._metrics
