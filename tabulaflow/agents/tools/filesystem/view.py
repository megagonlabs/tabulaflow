"""Filesystem viewer tool.

Views files and directories scoped to configured filesystem roots. Relative paths resolve against the working
directory; absolute paths are allowed only when permitted by the configured
roots, or when the tool is explicitly unrestricted.

Adapted from the Anthropic/OpenHands ``str_replace_editor`` pattern.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
import os
from pathlib import Path
from typing import ClassVar, NoReturn

from pydantic import BaseModel
from pydantic_ai import Tool, ToolReturn
from pydantic_ai.messages import BinaryContent

from tabulaflow.agents.media import select_pdf_pages, to_binary_content
from tabulaflow.agents.tools.filesystem.access import (
    _DEFAULT_ALLOWED_ROOTS,
    _DefaultAllowedRoots,
    _ResolvedFilesystemRoot,
    _resolve,
    _resolve_roots,
    FilesystemRoot,
)
from tabulaflow.core.media import DetectedMedia, detect_media


MAX_RESPONSE_LINES = 200
MAX_LINE_CHARS = 200
MAX_DIR_ENTRIES = 200
MAX_LOCAL_MEDIA_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class _ViewedMedia:
    description: str
    content: BinaryContent


class ViewToolMetrics(BaseModel):
    """Invocation and error counters for the filesystem viewer tool."""

    num_view: int = 0
    error_count: int = 0


class ViewTool:
    """View files and directories.

    By default, access is scoped to ``working_dir``.  Pass explicit
    ``allowed_roots`` to grant access to additional directories, or pass
    ``allowed_roots=None`` for unrestricted filesystem access.  Relative paths
    always resolve against ``working_dir``.
    """

    name: ClassVar = "view"

    def __init__(
        self,
        working_dir: str,
        allowed_roots: Sequence[FilesystemRoot] | None | _DefaultAllowedRoots = _DEFAULT_ALLOWED_ROOTS,
    ) -> None:
        self._working_dir = Path(working_dir).resolve()
        if not self._working_dir.is_dir():
            raise ValueError(f"working_dir is not a directory: {working_dir}")
        self._unrestricted = allowed_roots is None
        if isinstance(allowed_roots, _DefaultAllowedRoots):
            allowed_roots = [FilesystemRoot("working_dir", self._working_dir)]
        self._allowed_roots: tuple[_ResolvedFilesystemRoot, ...] = (
            () if allowed_roots is None else _resolve_roots(allowed_roots)
        )
        self._metrics = ViewToolMetrics()

    def _resolve(self, path: str) -> Path:
        """Resolve a path against working_dir and validate access policy."""
        return _resolve(
            path,
            working_dir=self._working_dir,
            allowed_roots=self._allowed_roots,
            unrestricted=self._unrestricted,
        )

    @staticmethod
    def _truncate_line(line: str) -> str:
        """Truncate a single line using head...tail."""
        if len(line) <= MAX_LINE_CHARS:
            return line
        marker = f"...({len(line)} chars)..."
        available = MAX_LINE_CHARS - len(marker)
        head = (available + 1) // 2
        tail = available // 2
        return line[:head] + marker + line[-tail:]

    def _make_numbered(
        self,
        content: str,
        start_line: int = 1,
    ) -> str:
        """Add line numbers to content and truncate long lines."""
        lines = [self._truncate_line(line) for line in content.split("\n")]
        return "\n".join(f"{i + start_line:6}\t{line}" for i, line in enumerate(lines))

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
            numbered = self._make_numbered("\n".join(selected))
            return header + numbered + f"\n\n(showing first {MAX_RESPONSE_LINES} of {num_lines} lines)"

        selected = lines[lo : hi + 1]
        truncated = False
        if len(selected) > MAX_RESPONSE_LINES:
            selected = selected[:MAX_RESPONSE_LINES]
            truncated = True
        numbered = self._make_numbered("\n".join(selected), start_line=lo + 1)
        if truncated:
            return header + numbered + f"\n\n(showing {MAX_RESPONSE_LINES} of {hi - lo + 1} lines in range)"
        return header + numbered

    async def _view_image(
        self,
        resolved: Path,
        path: str,
        view_range: list[int] | None,
        media: DetectedMedia,
    ) -> _ViewedMedia:
        if view_range is not None:
            return self._error("view_range is not supported for images.")

        size = resolved.stat().st_size
        if size > MAX_LOCAL_MEDIA_BYTES:
            return self._error(
                f"{path} is too large to read as an image ({size} bytes; limit {MAX_LOCAL_MEDIA_BYTES} bytes)."
            )
        data = await asyncio.to_thread(resolved.read_bytes)
        content = await asyncio.to_thread(to_binary_content, data, media_type=media.media_type)
        if len(content.data) > MAX_LOCAL_MEDIA_BYTES:
            return self._error(
                f"{path} is too large after normalization "
                f"({len(content.data)} bytes; limit {MAX_LOCAL_MEDIA_BYTES} bytes)."
            )
        description = f"Image: {path} ({content.media_type}, {len(content.data)} bytes)"
        return _ViewedMedia(description, content)

    async def _view_pdf(self, resolved: Path, path: str, view_range: list[int] | None) -> _ViewedMedia:
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

    async def __call__(
        self,
        path: str = ".",
        view_range: list[int] | None = None,
    ) -> str | ToolReturn:
        """View a file or list a directory.

        Images and PDFs are returned as native model content. For text files and
        directories, ``view_range`` selects an inclusive 1-indexed range. For PDFs,
        it selects an inclusive physical page range. Images do not accept a range.

        In restricted mode, paths must resolve under one of the configured
        filesystem roots.  In unrestricted mode, absolute paths are allowed.
        Relative paths always resolve against the working directory.

        Args:
            path: Relative path to the file or directory.
            view_range: Optional ``[start, end]`` for ``view`` (1-indexed).
                For files, selects a line range; for directories, an entry
                range for pagination; for PDFs, a physical page range.
        """
        try:
            result = await self.execute(path, view_range)
        except (ValueError, OSError) as exc:
            return f"(error: {exc})"
        if isinstance(result, _ViewedMedia):
            return ToolReturn(return_value=result.description, content=[result.content])
        return result

    async def execute(
        self,
        path: str = ".",
        view_range: list[int] | None = None,
    ) -> str | _ViewedMedia:
        """View one filesystem path."""
        resolved = self._resolve(path)
        self._metrics.num_view += 1
        if resolved.is_dir():
            return self._view_dir(resolved, path, view_range)
        if not resolved.is_file():
            return self._error(f"{path} does not exist.")

        with resolved.open("rb") as file:
            media = detect_media(file.read(256))
        if media is not None and media.media_type.startswith("image/"):
            return await self._view_image(resolved, path, view_range, media)
        if media is not None and media.media_type == "application/pdf":
            return await self._view_pdf(resolved, path, view_range)
        return self._view_file(resolved, path, view_range)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> ViewToolMetrics:
        return self._metrics
