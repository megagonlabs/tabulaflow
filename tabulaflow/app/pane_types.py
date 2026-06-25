"""Typed payload helpers for the browser output pane."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Required, TypedDict

ViewKind = Literal["chart", "data", "query"]
PaneSource = Literal["manual"]
_ARTIFACT_KIND_BY_PREFIX: dict[str, ViewKind] = {"V": "chart", "T": "data", "C": "data", "Q": "query"}


class PaneView(TypedDict, total=False):
    kind: Required[ViewKind]
    file: Required[str]
    meta: str


class PaneRecord(TypedDict):
    label: str | None
    views: list[PaneView]


class PaneTurn(TypedDict, total=False):
    title: Required[str]
    records: Required[list[PaneRecord]]
    user: str
    assistant: str
    source: PaneSource


def artifact_kind_for_path(path: Path) -> ViewKind:
    """Infer the pane view kind from a rendered artifact filename."""
    return _ARTIFACT_KIND_BY_PREFIX.get(path.name[:1], "data")


def view_payload(kind: ViewKind, file: str, *, meta: str | None = None) -> PaneView:
    """Build one view descriptor for the pane."""
    view: PaneView = {"kind": kind, "file": file}
    if meta:
        view["meta"] = meta
    return view


def record_payload(*, label: str | None, views: list[PaneView]) -> PaneRecord:
    """Build one result record descriptor for the pane."""
    return {"label": label, "views": views}


def turn_payload(
    *,
    title: str,
    records: list[PaneRecord],
    user: str | None = None,
    assistant: str | None = None,
    source: PaneSource | None = None,
) -> PaneTurn:
    """Build one output-pane turn."""
    turn: PaneTurn = {"title": title, "records": records}
    if user is not None:
        turn["user"] = user
    if assistant is not None:
        turn["assistant"] = assistant
    if source is not None:
        turn["source"] = source
    return turn


def manual_artifact_turn(
    path: Path,
    *,
    title: str | None = None,
    label: str | None = None,
    meta: str | None = None,
) -> PaneTurn:
    """Wrap an already-written artifact as a manual pane turn."""
    kind = artifact_kind_for_path(path)
    return turn_payload(
        title=title or kind,
        source="manual",
        records=[record_payload(label=label, views=[view_payload(kind, path.name, meta=meta)])],
    )
