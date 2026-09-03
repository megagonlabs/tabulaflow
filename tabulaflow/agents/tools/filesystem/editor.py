"""File editor tool.

Provides ``view``, ``write_file``, and ``str_replace`` commands scoped to
configured filesystem roots.  Relative paths resolve against the working
directory; absolute paths are allowed only when permitted by the configured
roots, or when the tool is explicitly unrestricted.

Adapted from the Anthropic/OpenHands ``str_replace_editor`` pattern.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
import os
import re
from pathlib import Path
from typing import ClassVar, Literal, NoReturn, overload

from pydantic import BaseModel
from pydantic_ai import Tool, ToolReturn
from pydantic_ai.messages import BinaryContent

from tabulaflow.agents.media import select_pdf_pages, to_binary_content
from tabulaflow.agents.tools.filesystem.access import (
    _DEFAULT_ALLOWED_ROOTS,
    _DefaultAllowedRoots,
    _ResolvedFileEditorRoot,
    _resolve,
    _resolve_roots,
    FileEditorRoot as FileEditorRoot,
)
from tabulaflow.core.media import detect_media


SNIPPET_CONTEXT_LINES = 4
MAX_RESPONSE_LINES = 200
MAX_RESPONSE_CHARS = 40000
MAX_DIR_ENTRIES = 200
MAX_LOCAL_MEDIA_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class _ViewedMedia:
    description: str
    content: BinaryContent


class FileEditorToolMetrics(BaseModel):
    """Command and error counters for the filesystem editor tool."""

    num_view: int = 0
    num_write_file: int = 0
    num_str_replace: int = 0
    error_count: int = 0


class FileEditorTool:
    """File editor with ``view``, ``write_file``, and ``str_replace`` commands.

    By default, access is scoped to ``working_dir``.  Pass explicit
    ``allowed_roots`` to grant access to additional directories, or pass
    ``allowed_roots=None`` for unrestricted filesystem access.  Relative paths
    always resolve against ``working_dir``.
    """

    name: ClassVar = "file_editor"

    def __init__(
        self,
        working_dir: str,
        allowed_roots: Sequence[FileEditorRoot] | None | _DefaultAllowedRoots = _DEFAULT_ALLOWED_ROOTS,
    ) -> None:
        self._working_dir = Path(working_dir).resolve()
        if not self._working_dir.is_dir():
            raise ValueError(f"working_dir is not a directory: {working_dir}")
        self._unrestricted = allowed_roots is None
        if isinstance(allowed_roots, _DefaultAllowedRoots):
            allowed_roots = [FileEditorRoot("working_dir", self._working_dir)]
        self._allowed_roots: tuple[_ResolvedFileEditorRoot, ...] = (
            () if allowed_roots is None else _resolve_roots(allowed_roots)
        )
        self._metrics = FileEditorToolMetrics()

    def _resolve(self, path: str, *, for_write: bool = False) -> Path:
        """Resolve a path against working_dir and validate access policy."""
        return _resolve(
            path,
            working_dir=self._working_dir,
            allowed_roots=self._allowed_roots,
            unrestricted=self._unrestricted,
            for_write=for_write,
        )

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

    def _error(self, msg: str) -> NoReturn:
        self._metrics.error_count += 1
        raise ValueError(msg)

    def _parse_range(self, view_range: list[int] | None, total: int) -> tuple[int, int]:
        """Parse and validate a 1-indexed [start, end] range.

        Returns (start, end) as 0-indexed inclusive bounds.
        """
        if not view_range:
            return (0, total - 1)
        if len(view_range) != 2:
            self._error("view_range must be a list of two integers [start, end].")
        start, end = view_range
        if start < 1:
            self._error(f"start must be >= 1, got {start}.")
        if start > total:
            self._error(f"start ({start}) is past the end (only {total} available).")
        if end > total:
            end = total  # clamp an over-long end to what's available
        if end < start:
            self._error(f"end ({end}) must be >= start ({start}).")
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
        lo, hi = self._parse_range(view_range, total)

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

        lo, hi = self._parse_range(view_range, num_lines)

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

    async def _view_image(self, resolved: Path, path: str, view_range: list[int] | None) -> _ViewedMedia | None:
        if not resolved.is_file():
            return None
        with resolved.open("rb") as file:
            detected = detect_media(file.read(256))
        if detected is None or not detected.media_type.startswith("image/"):
            return None
        if view_range is not None:
            return self._error("view_range is not supported for images.")

        size = resolved.stat().st_size
        if size > MAX_LOCAL_MEDIA_BYTES:
            return self._error(
                f"{path} is too large to read as an image ({size} bytes; limit {MAX_LOCAL_MEDIA_BYTES} bytes)."
            )
        data = await asyncio.to_thread(resolved.read_bytes)
        content = await asyncio.to_thread(to_binary_content, data, media_type=detected.media_type)
        if len(content.data) > MAX_LOCAL_MEDIA_BYTES:
            return self._error(
                f"{path} is too large after normalization "
                f"({len(content.data)} bytes; limit {MAX_LOCAL_MEDIA_BYTES} bytes)."
            )
        description = f"Image: {path} ({content.media_type}, {len(content.data)} bytes)"
        return _ViewedMedia(description, content)

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

    async def _view_pdf(self, resolved: Path, path: str, view_range: list[int] | None) -> _ViewedMedia:
        if not resolved.is_file():
            return self._error(f"{path} does not exist.")
        size = resolved.stat().st_size
        if size > MAX_LOCAL_MEDIA_BYTES:
            return self._error(
                f"{path} is too large to read as a PDF ({size} bytes; limit {MAX_LOCAL_MEDIA_BYTES} bytes)."
            )
        if view_range and len(view_range) != 2:
            return self._error("view_range must be a list of two integers [start, end].")

        data = await asyncio.to_thread(resolved.read_bytes)
        page_range = (view_range[0], view_range[1]) if view_range else None
        pdf = await asyncio.to_thread(select_pdf_pages, data, page_range)
        if len(pdf.data) > MAX_LOCAL_MEDIA_BYTES:
            return self._error(
                f"{path} is too large after page selection "
                f"({len(pdf.data)} bytes; limit {MAX_LOCAL_MEDIA_BYTES} bytes)."
            )
        content = to_binary_content(pdf.data, media_type="application/pdf")
        if pdf.first_page == 1 and pdf.last_page == pdf.total_pages:
            pages = f"{pdf.total_pages} {'page' if pdf.total_pages == 1 else 'pages'}"
        else:
            pages = f"pages {pdf.first_page}-{pdf.last_page} of {pdf.total_pages}"
        return _ViewedMedia(
            f"PDF: {path} ({pages}, {content.media_type}, {len(content.data)} bytes)",
            content,
        )

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

    @overload
    async def __call__(
        self,
        command: Literal["view"],
        path: str = ".",
        file_text: str | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        replace_all: bool = False,
        view_range: list[int] | None = None,
    ) -> str | ToolReturn: ...

    @overload
    async def __call__(
        self,
        command: Literal["write_file", "str_replace"],
        path: str = ".",
        file_text: str | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        replace_all: bool = False,
        view_range: list[int] | None = None,
    ) -> str: ...

    async def __call__(
        self,
        command: Literal["view", "write_file", "str_replace"],
        path: str = ".",
        file_text: str | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        replace_all: bool = False,
        view_range: list[int] | None = None,
    ) -> str | ToolReturn:
        """View and edit text files in the project directory.

        Commands:
        - ``view``: View a file (with optional line range) or list a directory (up to 2 levels deep).
          Images and PDFs are returned as native model content. For PDFs,
          ``view_range`` selects an inclusive 1-indexed page range. Images are
          read-only and do not accept ``view_range``.
        - ``write_file``: Create or overwrite a file with the given content.
        - ``str_replace``: Replace an exact occurrence of ``old_str`` with ``new_str``.
          ``old_str`` must match exactly (whitespace included) and be unique, unless
          ``replace_all`` is set. It must be the file's raw text — do NOT include the
          line-number prefixes shown by ``view``.

        In restricted mode, paths must resolve under one of the configured
        filesystem roots.  In unrestricted mode, absolute paths are allowed.
        Relative paths always resolve against the working directory.

        Args:
            command: One of ``"view"``, ``"write_file"``, ``"str_replace"``.
            path: Relative path to the file or directory.
            file_text: Content for ``write_file`` command.
            old_str: String to find for ``str_replace``.
            new_str: Replacement string for ``str_replace``.
            replace_all: For ``str_replace``, replace every occurrence instead of
                requiring ``old_str`` to be unique.
            view_range: Optional ``[start, end]`` for ``view`` (1-indexed).
                For files, selects a line range; for directories, an entry
                range for pagination; for PDFs, a physical page range.
        """
        try:
            result = await self.execute(command, path, file_text, old_str, new_str, replace_all, view_range)
        except (ValueError, OSError) as exc:
            return f"(error: {exc})"
        if isinstance(result, _ViewedMedia):
            return ToolReturn(return_value=result.description, content=[result.content])
        return result

    async def execute(
        self,
        command: Literal["view", "write_file", "str_replace"],
        path: str = ".",
        file_text: str | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        replace_all: bool = False,
        view_range: list[int] | None = None,
    ) -> str | _ViewedMedia:
        """Execute one filesystem editor command."""
        resolved = self._resolve(path, for_write=command in ("write_file", "str_replace"))

        if command in ("write_file", "str_replace") and self._is_pdf(resolved):
            return self._error(f"{path} is a PDF — PDFs are read-only; use the view command.")

        if command == "view":
            self._metrics.num_view += 1
            image = await self._view_image(resolved, path, view_range)
            if image is not None:
                return image
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
