"""Typed payload helpers for the browser output pane."""

from __future__ import annotations

from typing import Literal, Required, TypedDict

ViewKind = Literal["map", "chart", "data", "query"]
PaneSource = Literal["manual"]


class PaneCard(TypedDict):
    id: str
    label: str | None
    views: list[ViewKind]


class PaneTurn(TypedDict, total=False):
    id: int
    title: Required[str]
    cards: Required[list[PaneCard]]
    user: str
    assistant: str
    source: PaneSource


def card_payload(*, card_id: str, label: str | None, views: list[ViewKind]) -> PaneCard:
    """Build one result card descriptor for the pane."""
    return {"id": card_id, "label": label, "views": views}


def turn_payload(
    *,
    title: str,
    cards: list[PaneCard],
    user: str | None = None,
    assistant: str | None = None,
    source: PaneSource | None = None,
) -> PaneTurn:
    """Build one output-pane turn."""
    turn: PaneTurn = {"title": title, "cards": cards}
    if user is not None:
        turn["user"] = user
    if assistant is not None:
        turn["assistant"] = assistant
    if source is not None:
        turn["source"] = source
    return turn


def manual_card_turn(card: PaneCard, *, title: str | None = None) -> PaneTurn:
    """Wrap an already-written card-data payload as a manual pane turn."""
    return turn_payload(title=title or card["label"] or "preview", source="manual", cards=[card])
