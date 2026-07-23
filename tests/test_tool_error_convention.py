"""Tool string failures use the chat-visible ``(error: ...)`` convention."""

from __future__ import annotations

import ast
from pathlib import Path


_TOOLHUB = Path(__file__).resolve().parents[1] / "tabulaflow" / "toolhub"
_ALLOWED_PAREN_PREFIXES = (
    "(error:",
    "(no values to canonicalize",
    "(query executed successfully",
    "(statement executed successfully",
)


def _leading_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values:
        first = node.values[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    if isinstance(node, ast.Tuple) and node.elts:
        return _leading_string(node.elts[0])
    return None


def test_parenthesized_tool_failure_returns_start_with_error() -> None:
    offenders: list[str] = []
    for path in sorted(_TOOLHUB.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            leading = _leading_string(node.value)
            if leading is None or not leading.startswith("("):
                continue
            if not leading.startswith(_ALLOWED_PAREN_PREFIXES):
                rel = path.relative_to(_TOOLHUB.parents[1])
                offenders.append(f"{rel}:{node.lineno}: {leading!r}")

    assert offenders == []
