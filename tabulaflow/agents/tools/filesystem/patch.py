"""Filesystem-scoped tool wrapper for the pure apply-patch engine."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

from tabulaflow.agents.tools.filesystem.access import (
    _DEFAULT_ALLOWED_ROOTS,
    _DefaultAllowedRoots,
    _ResolvedFileEditorRoot,
    _resolve,
    _resolve_roots,
    FileEditorRoot,
)
from tabulaflow.agents.tools.filesystem.patch_engine import (
    ActionType,
    Commit,
    DiffError,
    Patch,
    apply_commit,
    identify_files_needed,
    load_files,
    patch_to_commit,
    text_to_patch,
    validate_add_paths,
)


class ApplyPatchToolMetrics(BaseModel):
    num_apply_patch: int = 0
    error_count: int = 0


class ApplyPatchTool:
    """Apply multi-file text patches."""

    name: ClassVar = "apply_patch"

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
        self._metrics = ApplyPatchToolMetrics()

    def _resolve(self, path: str, *, for_write: bool = False) -> Path:
        return _resolve(
            path,
            working_dir=self._working_dir,
            allowed_roots=self._allowed_roots,
            unrestricted=self._unrestricted,
            for_write=for_write,
        )

    @staticmethod
    def _reject_pdf(path: str, resolved: Path) -> None:
        if resolved.suffix.lower() == ".pdf":
            raise DiffError(f"{path} is a PDF and cannot be edited.")

    def _resolve_patch_path(self, path: str) -> Path:
        resolved = self._resolve(path, for_write=True)
        self._reject_pdf(path, resolved)
        return resolved

    def _open_text(self, path: str) -> str:
        resolved = self._resolve_patch_path(path)
        if not resolved.is_file():
            raise FileNotFoundError(path)
        try:
            return resolved.read_text()
        except UnicodeDecodeError as exc:
            raise DiffError(f"{path} is a binary file and cannot be edited.") from exc
        except OSError as exc:
            raise DiffError(f"could not read {path}: {exc}") from exc

    def _write_text(self, path: str, content: str) -> None:
        resolved = self._resolve_patch_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content)

    def _remove_file(self, path: str) -> None:
        resolved = self._resolve_patch_path(path)
        try:
            resolved.unlink()
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise DiffError(f"could not delete {path}: {exc}") from exc

    def _exists(self, path: str) -> bool:
        return self._resolve_patch_path(path).exists()

    def _validate_patch_paths(self, patch: Patch) -> None:
        for path, action in patch.actions.items():
            self._resolve_patch_path(path)
            if action.move_path:
                self._resolve_patch_path(action.move_path)

    def _process_patch(self, patch_text: str) -> tuple[int, Commit]:
        paths = identify_files_needed(patch_text)
        orig = load_files(paths, self._open_text)
        patch, fuzz = text_to_patch(patch_text, orig)
        self._validate_patch_paths(patch)
        validate_add_paths(patch, self._exists)
        commit = patch_to_commit(patch, orig)
        apply_commit(commit, self._write_text, self._remove_file)
        return fuzz, commit

    @staticmethod
    def _format_result(commit: Commit, fuzz: int) -> str:
        lines: list[str] = []
        for path, change in commit.changes.items():
            if change.type == ActionType.ADD:
                lines.append(f"A {path}")
            elif change.type == ActionType.DELETE:
                lines.append(f"D {path}")
            elif change.type == ActionType.UPDATE:
                if change.move_path:
                    lines.append(f"M {path} -> {change.move_path}")
                else:
                    lines.append(f"M {path}")
        if fuzz > 0:
            lines.append(f"(fuzzy-matched, fuzz={fuzz})")
        return "\n".join(lines) if lines else "Done!"

    async def __call__(self, patch: str) -> str:
        """Apply a multi-file text patch. The preferred tool for editing files.

        The patch must use the V4A envelope format with ``*** Begin Patch`` and
        ``*** End Patch``.

        Args:
            patch: Patch text containing one or more add, update, delete, or
                move operations.
        """
        try:
            return await self.execute(patch)
        except (ValueError, OSError) as exc:
            return f"(error: {exc})"

    async def execute(self, patch: str) -> str:
        """Apply one V4A patch."""
        self._metrics.num_apply_patch += 1
        try:
            fuzz, commit = self._process_patch(patch)
        except DiffError as exc:
            self._metrics.error_count += 1
            raise ValueError(str(exc)) from exc
        except (ValueError, OSError):
            self._metrics.error_count += 1
            raise
        return self._format_result(commit, fuzz)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> ApplyPatchToolMetrics:
        return self._metrics
