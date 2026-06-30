"""Typed payload helpers for the browser output pane."""

from __future__ import annotations

from typing import Literal, Required, TypedDict

ViewKind = Literal["chart", "data", "query"]
PaneSource = Literal["manual"]


class PaneRecord(TypedDict):
    id: str
    label: str | None
    views: list[ViewKind]


class PaneTurn(TypedDict, total=False):
    id: int
    title: Required[str]
    records: Required[list[PaneRecord]]
    user: str
    assistant: str
    source: PaneSource


def record_payload(*, record_id: str, label: str | None, views: list[ViewKind]) -> PaneRecord:
    """Build one result record descriptor for the pane."""
    return {"id": record_id, "label": label, "views": views}


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


def manual_record_turn(record: PaneRecord, *, title: str | None = None) -> PaneTurn:
    """Wrap an already-written record-data payload as a manual pane turn."""
    return turn_payload(title=title or record["label"] or "preview", source="manual", records=[record])
