"""File editor tool.

Provides ``view``, ``write_file``, and ``str_replace`` commands scoped to a
working directory.  Paths are always relative to the working directory and
validated to prevent directory traversal.

Adapted from the Anthropic/OpenHands ``str_replace_editor`` pattern.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel
from pydantic_ai import Tool

from tabulaflow.toolhub.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    ScopedMessageStore,
    make_marked,
    make_snippet,
)


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

    def __init__(self, working_dir: str, message_store: ScopedMessageStore | None = None) -> None:
        self._working_dir = Path(working_dir).resolve()
        if not self._working_dir.is_dir():
            raise ValueError(f"working_dir is not a directory: {working_dir}")
        # When present, a viewed PDF's extracted text is mirrored to the message store
        # so the agent can run extraction tools on its message_id (PDFs only — other
        # returns are not mirrored).
        self._message_store = message_store
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
        if start > total:
            return self._error(f"start ({start}) is past the end (only {total} available).")
        if end == -1 or end > total:
            end = total  # clamp an over-long end to what's available
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

    @staticmethod
    def _is_pdf(resolved: Path) -> bool:
        """Detect a PDF by extension or ``%PDF-`` magic bytes."""
        if resolved.suffix.lower() == ".pdf":
            return True
        try:
            with open(resolved, "rb") as f:
                return f.read(5) == b"%PDF-"
        except OSError:
            return False

    async def _view_pdf(self, resolved: Path, path: str, view_range: list[int] | None) -> str:
        """View a PDF as its full extracted text (pypdf), the same way the web browser does.

        Returns the whole document (page-marked) untruncated: when offloaded to the
        message store it lands in ``_internal.messages`` so the agent can run
        ``extract_rows_from_documents`` / ``run_subagent_for_each_row`` over it.
        Text-layer extraction only — scanned/image-only PDFs return a clear notice.
        ``view_range`` does not apply (the full document is returned).
        """
        from tabulaflow.toolhub.pdf_extract import extract_pdf_text

        if view_range is not None:
            return self._error(
                "view_range is not supported for PDFs — view returns the full document text. "
                "Re-run view without view_range."
            )
        if not resolved.is_file():
            return self._error(f"{path} does not exist.")
        try:
            data = resolved.read_bytes()
        except OSError as e:
            return self._error(f"could not read {path}: {e}")

        try:
            _, body = await asyncio.to_thread(extract_pdf_text, data)
        except Exception as e:
            return self._error(f"could not parse {path} as a PDF: {e}")
        if not body:
            return self._error(f"{path} has no extractable text layer (likely scanned or image-only).")

        npages = len(re.findall(r"--- Page \d+ ---", body))
        text = f"PDF: {path} ({npages} page(s) with text)\n{body}"

        # Mirror to the message store (PDFs only) so the agent can extract over the
        # full document by message_id; long output is replaced with a head+tail
        # snippet pointing back at the stored row.
        if self._message_store is None:
            return text
        message_id = await self._message_store.add(kind="tool_return", content=text, tool_name=self.name)
        if len(text) <= MESSAGE_THRESHOLD_CHARS:
            return make_marked(message_id, text)
        return make_snippet(message_id, text)

    def _write_file(self, resolved: Path, path: str, file_text: str) -> str:
        is_new = not resolved.exists()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(file_text)
        num_lines = file_text.count("\n") + (1 if file_text and not file_text.endswith("\n") else 0)
        action = "Created" if is_new else "Wrote"
        return f"{action}: {path} ({num_lines} lines)"

    def _str_replace(self, resolved: Path, path: str, old_str: str, new_str: str, replace_all: bool = False) -> str:
        if not resolved.is_file():
            return self._error(f"{path} does not exist.")
        if old_str == new_str:
            return self._error("old_str and new_str are identical.")

        try:
            content = resolved.read_text()
        except (UnicodeDecodeError, ValueError):
            return self._error(f"{path} is a binary file and cannot be edited.")

        # Exact, whitespace-sensitive matching only — no fuzzy fallback. A lenient
        # match can silently land an edit that loses surrounding whitespace, so an
        # imperfect old_str fails loudly instead.
        count = content.count(old_str)
        if count == 0:
            return self._error(f"old_str not found in {path}.")
        if count > 1 and not replace_all:
            line_numbers = sorted(
                content.count("\n", 0, m.start()) + 1 for m in re.finditer(re.escape(old_str), content)
            )
            return self._error(
                f"old_str found {count} times in {path} (lines {line_numbers}). It must be unique — "
                "include more context, or set replace_all=true to replace every occurrence."
            )

        new_content = content.replace(old_str, new_str)
        resolved.write_text(new_content)

        # Show a snippet around the first replacement (with the count when replacing all).
        replacement_line = content.count("\n", 0, content.find(old_str)) + 1
        start = max(1, replacement_line - SNIPPET_CONTEXT_LINES)
        end = replacement_line + SNIPPET_CONTEXT_LINES + new_str.count("\n")
        snippet_lines = new_content.split("\n")[start - 1 : end]
        per_line = MAX_RESPONSE_CHARS // max(len(snippet_lines), 1)
        snippet = self._make_numbered("\n".join(snippet_lines), start_line=start, max_line_chars=per_line)

        label = f"Edited {path}" + (f" ({count} occurrences replaced)" if replace_all and count > 1 else "")
        return f"{label}. Snippet:\n{snippet}"

    # -- main entry point -----------------------------------------------------

    async def __call__(
        self,
        command: Literal["view", "write_file", "str_replace"],
        path: str = ".",
        file_text: str | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        replace_all: bool = False,
        view_range: list[int] | None = None,
    ) -> str:
        """View and edit text files in the project directory.

        Commands:
        - ``view``: View a file (with optional line range) or list a directory (up to 2 levels deep).
          A PDF is shown as its full extracted text (text-layer only — a scanned/image-only PDF
          returns a no-text notice). PDFs are read-only and ignore ``view_range``.
        - ``write_file``: Create or overwrite a file with the given content.
        - ``str_replace``: Replace an exact occurrence of ``old_str`` with ``new_str``.
          ``old_str`` must match exactly (whitespace included) and be unique, unless
          ``replace_all`` is set. It must be the file's raw text — do NOT include the
          line-number prefixes shown by ``view``.

        All paths are relative to the project directory.

        Args:
            command: One of ``"view"``, ``"write_file"``, ``"str_replace"``.
            path: Relative path to the file or directory.
            file_text: Content for ``write_file`` command.
            old_str: String to find for ``str_replace``.
            new_str: Replacement string for ``str_replace``.
            replace_all: For ``str_replace``, replace every occurrence instead of
                requiring ``old_str`` to be unique.
            view_range: Optional ``[start, end]`` for ``view`` (1-indexed,
                end=-1 means last). For files, selects a line range; for
                directories, an entry range for pagination. Not used for PDFs.
        """
        try:
            resolved = self._resolve(path)
        except ValueError as e:
            return self._error(str(e))

        if command in ("write_file", "str_replace") and self._is_pdf(resolved):
            return self._error(f"{path} is a PDF — PDFs are read-only; use the view command.")

        if command == "view":
            self._metrics.num_view += 1
            if self._is_pdf(resolved):
                return await self._view_pdf(resolved, path, view_range)
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
            return self._str_replace(resolved, path, old_str, new_str, replace_all)
        else:
            return self._error(f"unknown command '{command}'. Use view, write_file, or str_replace.")

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> FileEditorToolMetrics:
        return self._metrics
