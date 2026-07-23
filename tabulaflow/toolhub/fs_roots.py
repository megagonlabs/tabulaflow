"""Shared filesystem-root policy for host file tools."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class FileEditorRoot:
    """A filesystem root that a host file tool may access.

    Args:
        name: Human-readable root label used in error messages.
        path: Root directory path.
        writable: Whether mutating commands may write under this root.
    """

    name: str
    path: str | Path
    writable: bool = True


@dataclass(frozen=True)
class _ResolvedFileEditorRoot:
    name: str
    path: Path
    writable: bool


class _DefaultAllowedRoots:
    pass


_DEFAULT_ALLOWED_ROOTS: Final = _DefaultAllowedRoots()


def _resolve_roots(roots: Sequence[FileEditorRoot]) -> tuple[_ResolvedFileEditorRoot, ...]:
    resolved_roots: list[_ResolvedFileEditorRoot] = []
    for root in roots:
        name = root.name.strip()
        if not name:
            raise ValueError("allowed root name must be non-empty")
        resolved = Path(root.path).resolve()
        if not resolved.is_dir():
            raise ValueError(f"allowed root is not a directory: {root.path}")
        resolved_roots.append(_ResolvedFileEditorRoot(name, resolved, root.writable))
    if not resolved_roots:
        raise ValueError("allowed_roots must contain at least one root, or be None for unrestricted access")
    return tuple(resolved_roots)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _root_for(
    resolved: Path,
    allowed_roots: Sequence[_ResolvedFileEditorRoot],
) -> _ResolvedFileEditorRoot | None:
    for root in allowed_roots:
        if _is_relative_to(resolved, root.path):
            return root
    return None


def _format_allowed_roots(allowed_roots: Sequence[_ResolvedFileEditorRoot]) -> str:
    return ", ".join(f"{root.name}={root.path}" for root in allowed_roots)


def _resolve(
    path: str,
    *,
    working_dir: Path,
    allowed_roots: Sequence[_ResolvedFileEditorRoot],
    unrestricted: bool,
    for_write: bool = False,
) -> Path:
    p = Path(path)
    resolved = p.resolve() if p.is_absolute() else (working_dir / p).resolve()
    if unrestricted:
        return resolved

    root = _root_for(resolved, allowed_roots)
    if root is None:
        raise ValueError(f"Path is outside the allowed roots ({_format_allowed_roots(allowed_roots)}): {path}")
    if for_write and not root.writable:
        raise ValueError(f"Path is under read-only root '{root.name}': {path}")
    return resolved
