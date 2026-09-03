"""Structured text-file editing tool."""

from collections.abc import Sequence
from pathlib import Path
import re
from typing import ClassVar, Literal

from pydantic import BaseModel
from pydantic_ai import Tool

from tabulaflow.agents.tools.filesystem.access import (
    _DEFAULT_ALLOWED_ROOTS,
    _DefaultAllowedRoots,
    _ResolvedFilesystemRoot,
    _resolve,
    _resolve_roots,
    FilesystemRoot,
)


SNIPPET_CONTEXT_LINES = 4
MAX_RESPONSE_CHARS = 40000


class EditFileToolMetrics(BaseModel):
    """Command and error counters for structured file editing."""

    num_write: int = 0
    num_replace: int = 0
    error_count: int = 0


class EditFileTool:
    """Write files or replace exact text within them."""

    name: ClassVar = "edit_file"

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
        self._metrics = EditFileToolMetrics()

    def _resolve(self, path: str) -> Path:
        return _resolve(
            path,
            working_dir=self._working_dir,
            allowed_roots=self._allowed_roots,
            unrestricted=self._unrestricted,
            for_write=True,
        )

    @staticmethod
    def _reject_pdf(path: str, resolved: Path) -> None:
        if resolved.suffix.lower() == ".pdf":
            raise ValueError(f"{path} is a PDF and cannot be edited.")
        try:
            if resolved.is_file():
                with resolved.open("rb") as file:
                    if file.read(5) == b"%PDF-":
                        raise ValueError(f"{path} is a PDF and cannot be edited.")
        except OSError:
            pass

    @staticmethod
    def _numbered(content: str, start_line: int) -> str:
        lines = content.split("\n")
        per_line = MAX_RESPONSE_CHARS // max(len(lines), 1)
        numbered = []
        for index, line in enumerate(lines, start_line):
            if len(line) > per_line:
                half = per_line // 2
                if half == 0:
                    line = f"...({len(line)} chars)..."
                else:
                    line = line[:half] + f"...({len(line)} chars)..." + line[-half:]
            numbered.append(f"{index:6}\t{line}")
        return "\n".join(numbered)

    def _write(self, resolved: Path, path: str, new_text: str) -> str:
        is_new = not resolved.exists()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(new_text)
        num_lines = new_text.count("\n") + (1 if new_text and not new_text.endswith("\n") else 0)
        action = "Created" if is_new else "Wrote"
        return f"{action}: {path} ({num_lines} lines)"

    def _replace(
        self,
        resolved: Path,
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool,
    ) -> str:
        if not resolved.is_file():
            raise ValueError(f"{path} does not exist.")
        if old_text == new_text:
            raise ValueError("old_text and new_text are identical.")
        try:
            content = resolved.read_text()
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"{path} is a binary file and cannot be edited.") from exc

        count = content.count(old_text)
        if count == 0:
            raise ValueError(f"old_text not found in {path}.")
        if count > 1 and not replace_all:
            line_numbers = sorted(
                content.count("\n", 0, match.start()) + 1 for match in re.finditer(re.escape(old_text), content)
            )
            raise ValueError(
                f"old_text found {count} times in {path} (lines {line_numbers}). It must be unique — "
                "include more context, or set replace_all=true to replace every occurrence."
            )

        new_content = content.replace(old_text, new_text)
        resolved.write_text(new_content)
        replacement_line = content.count("\n", 0, content.find(old_text)) + 1
        start = max(1, replacement_line - SNIPPET_CONTEXT_LINES)
        end = replacement_line + SNIPPET_CONTEXT_LINES + new_text.count("\n")
        snippet = self._numbered("\n".join(new_content.split("\n")[start - 1 : end]), start)
        label = f"Edited {path}" + (f" ({count} occurrences replaced)" if replace_all and count > 1 else "")
        return f"{label}. Snippet:\n{snippet}"

    async def __call__(
        self,
        command: Literal["write", "replace"],
        path: str,
        new_text: str,
        old_text: str | None = None,
        replace_all: bool = False,
    ) -> str:
        """Write a text file or replace exact text within one.

        Args:
            command: ``write`` to create or overwrite a file, or ``replace`` to
                replace text in an existing file.
            path: Path to the text file.
            new_text: Complete file content for ``write``; replacement text for
                ``replace``.
            old_text: Exact, whitespace-sensitive text to find for ``replace``.
            replace_all: Replace every occurrence instead of requiring a unique
                match. Only valid for ``replace``.
        """
        try:
            return await self.execute(command, path, new_text, old_text, replace_all)
        except (ValueError, OSError) as exc:
            return f"(error: {exc})"

    async def execute(
        self,
        command: Literal["write", "replace"],
        path: str,
        new_text: str,
        old_text: str | None = None,
        replace_all: bool = False,
    ) -> str:
        """Execute one structured file edit."""
        try:
            resolved = self._resolve(path)
            self._reject_pdf(path, resolved)
            if command == "write":
                if old_text is not None:
                    raise ValueError("old_text is not valid for the write command.")
                if replace_all:
                    raise ValueError("replace_all is not valid for the write command.")
                self._metrics.num_write += 1
                return self._write(resolved, path, new_text)
            if command == "replace":
                if old_text is None:
                    raise ValueError("old_text is required for the replace command.")
                self._metrics.num_replace += 1
                return self._replace(resolved, path, old_text, new_text, replace_all)
            raise ValueError(f"unknown command '{command}'. Use write or replace.")
        except (ValueError, OSError):
            self._metrics.error_count += 1
            raise

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> EditFileToolMetrics:
        return self._metrics
