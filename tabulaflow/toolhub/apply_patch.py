"""Pure engine for OpenAI V4A ``apply_patch`` patches."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

from tabulaflow.toolhub.fs_roots import (
    _DEFAULT_ALLOWED_ROOTS,
    _DefaultAllowedRoots,
    _ResolvedFileEditorRoot,
    _resolve,
    _resolve_roots,
    FileEditorRoot,
)

_UNICODE_NORMALIZATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u00a0": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2004": " ",
        "\u2005": " ",
        "\u2006": " ",
        "\u2007": " ",
        "\u2008": " ",
        "\u2009": " ",
        "\u200a": " ",
        "\u202f": " ",
        "\u205f": " ",
        "\u3000": " ",
    }
)


class DiffError(ValueError):
    """Raised for invalid or malformed patch text."""


class ActionType(str, Enum):
    ADD = "add"
    DELETE = "delete"
    UPDATE = "update"


class ApplyPatchToolMetrics(BaseModel):
    num_apply_patch: int = 0
    error_count: int = 0


@dataclass
class FileChange:
    type: ActionType
    old_content: str | None = None
    new_content: str | None = None
    move_path: str | None = None


@dataclass
class Commit:
    changes: dict[str, FileChange] = field(default_factory=dict)


@dataclass
class Chunk:
    orig_index: int = -1
    del_lines: list[str] = field(default_factory=list)
    ins_lines: list[str] = field(default_factory=list)


@dataclass
class PatchAction:
    type: ActionType
    new_file: str | None = None
    chunks: list[Chunk] = field(default_factory=list)
    move_path: str | None = None


@dataclass
class Patch:
    actions: dict[str, PatchAction] = field(default_factory=dict)


@dataclass
class _Section:
    context: list[str]
    chunks: list[Chunk]
    end_index: int
    eof: bool


@dataclass
class Parser:
    current_files: dict[str, str]
    lines: list[str]
    index: int = 0
    patch: Patch = field(default_factory=Patch)
    fuzz: int = 0

    def is_done(self, prefixes: tuple[str, ...] | None = None) -> bool:
        if self.index >= len(self.lines):
            return True
        return prefixes is not None and self.lines[self.index].startswith(prefixes)

    def startswith(self, prefix: str | tuple[str, ...]) -> bool:
        if self.index >= len(self.lines):
            raise self.error(f"Unexpected end of patch while looking for {prefix!r}")
        return self.lines[self.index].startswith(prefix)

    def read_str(self, prefix: str = "", *, return_everything: bool = False) -> str:
        if self.index >= len(self.lines):
            raise self.error(f"Unexpected end of patch while looking for {prefix!r}")
        line = self.lines[self.index]
        if line.startswith(prefix):
            text = line if return_everything else line[len(prefix) :]
            self.index += 1
            return text
        return ""

    def error(self, message: str, *, line_index: int | None = None) -> DiffError:
        line_number = (self.index if line_index is None else line_index) + 1
        return DiffError(f"line {line_number}: {message}")

    def parse(self) -> None:
        while not self.is_done(("*** End Patch",)):
            path = self.read_str("*** Update File: ")
            if path:
                if path in self.patch.actions:
                    raise self.error(f"Update File Error: Duplicate Path: {path}", line_index=self.index - 1)
                move_to = self.read_str("*** Move to: ")
                if path not in self.current_files:
                    raise self.error(f"Update File Error: Missing File: {path}", line_index=self.index - 1)
                action = self.parse_update_file(self.current_files[path])
                action.move_path = move_to
                self.patch.actions[path] = action
                continue

            path = self.read_str("*** Delete File: ")
            if path:
                if path in self.patch.actions:
                    raise self.error(f"Delete File Error: Duplicate Path: {path}", line_index=self.index - 1)
                if path not in self.current_files:
                    raise self.error(f"Delete File Error: Missing File: {path}", line_index=self.index - 1)
                self.patch.actions[path] = PatchAction(type=ActionType.DELETE)
                continue

            path = self.read_str("*** Add File: ")
            if path:
                if path in self.patch.actions:
                    raise self.error(f"Add File Error: Duplicate Path: {path}", line_index=self.index - 1)
                self.patch.actions[path] = self.parse_add_file()
                continue

            raise self.error(f"Unknown Line: {self.lines[self.index]}")

        if not self.startswith("*** End Patch"):
            raise self.error("Missing End Patch")
        self.index += 1

    def parse_update_file(self, text: str) -> PatchAction:
        action = PatchAction(type=ActionType.UPDATE)
        lines = text.split("\n")
        index = 0
        while not self.is_done(
            (
                "*** End Patch",
                "*** Update File:",
                "*** Delete File:",
                "*** Add File:",
                "*** End of File",
            )
        ):
            def_str = self.read_str("@@ ")
            section_str = ""
            if not def_str and self.index < len(self.lines) and self.lines[self.index] == "@@":
                section_str = self.lines[self.index]
                self.index += 1
            if not (def_str or section_str or index == 0):
                raise self.error(f"Invalid Line:\n{self.lines[self.index]}")

            if def_str.strip():
                found = False
                if not any(s == def_str for s in lines[:index]):
                    for i, s in enumerate(lines[index:], index):
                        if s == def_str:
                            index = i + 1
                            found = True
                            break
                if not found and not any(s.strip() == def_str.strip() for s in lines[:index]):
                    for i, s in enumerate(lines[index:], index):
                        if s.strip() == def_str.strip():
                            index = i + 1
                            self.fuzz += 1
                            found = True
                            break

            section = peek_next_section(self.lines, self.index)
            next_chunk_text = "\n".join(section.context)
            new_index, fuzz = find_context(lines, section.context, index, section.eof)
            if new_index == -1:
                if section.eof:
                    raise self.error(f"Invalid EOF Context {index}:\n{next_chunk_text}")
                raise self.error(f"Invalid Context {index}:\n{next_chunk_text}")
            self.fuzz += fuzz
            for chunk in section.chunks:
                chunk.orig_index += new_index
                action.chunks.append(chunk)
            index = new_index + len(section.context)
            self.index = section.end_index
        return action

    def parse_add_file(self) -> PatchAction:
        lines: list[str] = []
        while not self.is_done(("*** End Patch", "*** Update File:", "*** Delete File:", "*** Add File:")):
            line_index = self.index
            s = self.read_str()
            if not s.startswith("+"):
                raise self.error(f"Invalid Add File Line: {s}", line_index=line_index)
            lines.append(s[1:])
        return PatchAction(type=ActionType.ADD, new_file="\n".join(lines))


def assemble_changes(orig: dict[str, str | None], dest: dict[str, str | None]) -> Commit:
    commit = Commit()
    for path in sorted(set(orig.keys()).union(dest.keys())):
        old_content = orig.get(path)
        new_content = dest.get(path)
        if old_content == new_content:
            continue
        if old_content is not None and new_content is not None:
            commit.changes[path] = FileChange(
                type=ActionType.UPDATE,
                old_content=old_content,
                new_content=new_content,
            )
        elif new_content is not None:
            commit.changes[path] = FileChange(type=ActionType.ADD, new_content=new_content)
        elif old_content is not None:
            commit.changes[path] = FileChange(type=ActionType.DELETE, old_content=old_content)
    return commit


def _normalize_unicode_context(line: str) -> str:
    return line.strip().translate(_UNICODE_NORMALIZATION)


def find_context_core(lines: list[str], context: list[str], start: int, *, stop: int | None = None) -> tuple[int, int]:
    if not context:
        return start, 0
    if len(context) > len(lines):
        return -1, 0

    start = max(start, 0)
    last_start = len(lines) - len(context)
    if stop is None:
        stop = last_start + 1
    stop = min(stop, last_start + 1)
    if start >= stop:
        return -1, 0

    for i in range(start, stop):
        if lines[i : i + len(context)] == context:
            return i, 0
    for i in range(start, stop):
        if [s.rstrip() for s in lines[i : i + len(context)]] == [s.rstrip() for s in context]:
            return i, 1
    for i in range(start, stop):
        if [s.strip() for s in lines[i : i + len(context)]] == [s.strip() for s in context]:
            return i, 100
    for i in range(start, stop):
        if [_normalize_unicode_context(s) for s in lines[i : i + len(context)]] == [
            _normalize_unicode_context(s) for s in context
        ]:
            return i, 1000
    return -1, 0


def find_context(lines: list[str], context: list[str], start: int, eof: bool) -> tuple[int, int]:
    if eof:
        content_len = len(lines)
        if lines and lines[-1] == "" and (not context or context[-1] != ""):
            content_len -= 1
        eof_start = content_len - len(context)
        return find_context_core(lines, context, eof_start, stop=eof_start + 1)
    return find_context_core(lines, context, start)


def peek_next_section(lines: list[str], index: int) -> _Section:
    old: list[str] = []
    del_lines: list[str] = []
    ins_lines: list[str] = []
    chunks: list[Chunk] = []
    mode = "keep"
    orig_index = index
    while index < len(lines):
        s = lines[index]
        if s.startswith(
            (
                "@@",
                "*** End Patch",
                "*** Update File:",
                "*** Delete File:",
                "*** Add File:",
                "*** End of File",
            )
        ):
            break
        if s == "***":
            break
        if s.startswith("***"):
            raise DiffError(f"line {index + 1}: Invalid Line: {s}")
        index += 1
        last_mode = mode
        if s == "":
            s = " "
        if s[0] == "+":
            mode = "add"
        elif s[0] == "-":
            mode = "delete"
        elif s[0] == " ":
            mode = "keep"
        else:
            raise DiffError(f"line {index}: Invalid Line: {s}")
        s = s[1:]
        if mode == "keep" and last_mode != mode:
            if ins_lines or del_lines:
                chunks.append(Chunk(orig_index=len(old) - len(del_lines), del_lines=del_lines, ins_lines=ins_lines))
            del_lines = []
            ins_lines = []
        if mode == "delete":
            del_lines.append(s)
            old.append(s)
        elif mode == "add":
            ins_lines.append(s)
        elif mode == "keep":
            old.append(s)

    if ins_lines or del_lines:
        chunks.append(Chunk(orig_index=len(old) - len(del_lines), del_lines=del_lines, ins_lines=ins_lines))
    if index < len(lines) and lines[index] == "*** End of File":
        return _Section(context=old, chunks=chunks, end_index=index + 1, eof=True)
    if index == orig_index:
        line = lines[index] if index < len(lines) else "<end of patch>"
        raise DiffError(f"line {index + 1}: Nothing in this section - index={index} {line}")
    return _Section(context=old, chunks=chunks, end_index=index, eof=False)


def _patch_lines(text: str) -> list[str]:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def text_to_patch(text: str, orig: dict[str, str]) -> tuple[Patch, int]:
    lines = _patch_lines(text)
    if not lines or lines[0] != "*** Begin Patch":
        raise DiffError("line 1: Invalid patch text: first line must be '*** Begin Patch'")
    if len(lines) < 2 or lines[-1] != "*** End Patch":
        raise DiffError("Invalid patch text: last line must be '*** End Patch'")

    parser = Parser(current_files=orig, lines=lines, index=1)
    parser.parse()
    return parser.patch, parser.fuzz


def identify_files_needed(text: str) -> list[str]:
    result: set[str] = set()
    for line in _patch_lines(text):
        if line.startswith("*** Update File: "):
            result.add(line[len("*** Update File: ") :])
        if line.startswith("*** Delete File: "):
            result.add(line[len("*** Delete File: ") :])
    return list(result)


def _get_updated_file(text: str, action: PatchAction, path: str) -> str:
    if action.type != ActionType.UPDATE:
        raise DiffError(f"_get_updated_file: {path}: expected update action")
    orig_lines = text.split("\n")
    dest_lines: list[str] = []
    orig_index = 0
    dest_index = 0
    for chunk in action.chunks:
        if chunk.orig_index > len(orig_lines):
            raise DiffError(
                f"_get_updated_file: {path}: chunk.orig_index {chunk.orig_index} > len(lines) {len(orig_lines)}"
            )
        if orig_index > chunk.orig_index:
            raise DiffError(f"_get_updated_file: {path}: orig_index {orig_index} > chunk.orig_index {chunk.orig_index}")
        delta = chunk.orig_index - orig_index
        dest_lines.extend(orig_lines[orig_index : chunk.orig_index])
        orig_index += delta
        dest_index += delta
        dest_lines.extend(chunk.ins_lines)
        dest_index += len(chunk.ins_lines)
        orig_index += len(chunk.del_lines)
    dest_lines.extend(orig_lines[orig_index:])
    delta = len(orig_lines) - orig_index
    orig_index += delta
    dest_index += delta
    if orig_index != len(orig_lines) or dest_index != len(dest_lines):
        raise DiffError(f"_get_updated_file: {path}: internal index mismatch")
    return "\n".join(dest_lines)


def patch_to_commit(patch: Patch, orig: dict[str, str]) -> Commit:
    commit = Commit()
    for path, action in patch.actions.items():
        if action.type == ActionType.DELETE:
            commit.changes[path] = FileChange(type=ActionType.DELETE, old_content=orig[path])
        elif action.type == ActionType.ADD:
            if action.new_file is None:
                raise DiffError(f"Add File Error: Missing new content: {path}")
            commit.changes[path] = FileChange(
                type=ActionType.ADD, new_content=normalize_trailing_newline(action.new_file)
            )
        elif action.type == ActionType.UPDATE:
            new_content = normalize_trailing_newline(_get_updated_file(text=orig[path], action=action, path=path))
            commit.changes[path] = FileChange(
                type=ActionType.UPDATE,
                old_content=orig[path],
                new_content=new_content,
                move_path=action.move_path,
            )
    return commit


def normalize_trailing_newline(text: str) -> str:
    return text.rstrip("\n") + "\n"


def load_files(paths: list[str], open_fn: Callable[[str], str]) -> dict[str, str]:
    orig: dict[str, str] = {}
    for path in paths:
        try:
            orig[path] = open_fn(path)
        except FileNotFoundError as exc:
            raise DiffError(f"Missing File: {path}") from exc
    return orig


def validate_add_paths(patch: Patch, exists_fn: Callable[[str], bool] | None) -> None:
    if exists_fn is None:
        return
    for path, action in patch.actions.items():
        if action.type == ActionType.ADD and exists_fn(path):
            raise DiffError(f"Add File Error: File already exists: {path}")


def apply_commit(
    commit: Commit,
    write_fn: Callable[[str, str], None],
    remove_fn: Callable[[str], None],
) -> None:
    for path, change in commit.changes.items():
        if change.type == ActionType.DELETE:
            remove_fn(path)
        elif change.type == ActionType.ADD:
            if change.new_content is None:
                raise DiffError(f"Add File Error: Missing new content: {path}")
            write_fn(path, change.new_content)
        elif change.type == ActionType.UPDATE:
            if change.new_content is None:
                raise DiffError(f"Update File Error: Missing new content: {path}")
            if change.move_path:
                write_fn(change.move_path, change.new_content)
                remove_fn(path)
            else:
                write_fn(path, change.new_content)


def process_patch(
    text: str,
    open_fn: Callable[[str], str],
    write_fn: Callable[[str, str], None],
    remove_fn: Callable[[str], None],
    exists_fn: Callable[[str], bool] | None = None,
) -> tuple[str, int, Commit]:
    """Process a patch string and apply it with injected I/O callables."""
    paths = identify_files_needed(text)
    orig = load_files(paths, open_fn)
    patch, fuzz = text_to_patch(text, orig)
    validate_add_paths(patch, exists_fn)
    commit = patch_to_commit(patch, orig)
    apply_commit(commit, write_fn, remove_fn)
    return "Done!", fuzz, commit


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

    def _error(self, msg: str) -> str:
        self._metrics.error_count += 1
        return f"(error: {msg})"

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
        """Apply a multi-file text patch.

        The patch must use the V4A envelope format with ``*** Begin Patch`` and
        ``*** End Patch``.

        Args:
            patch: Patch text containing one or more add, update, delete, or
                move operations.
        """
        self._metrics.num_apply_patch += 1
        try:
            fuzz, commit = self._process_patch(patch)
        except (DiffError, ValueError, OSError) as exc:
            return self._error(str(exc))
        return self._format_result(commit, fuzz)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> ApplyPatchToolMetrics:
        return self._metrics
