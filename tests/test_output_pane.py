from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from tabulaflow.app.render.cards import render_record_card
from tabulaflow.app.pane import OutputPane


def test_output_pane_serves_text_only_turn(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        pane.push(
            {
                "title": "summarize",
                "user": "Summarize the latest result.",
                "assistant": "The result has three rows.",
                "records": [],
            }
        )

        assert pane.url is not None
        with urllib.request.urlopen(f"{pane.url}__index__", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))

        assert payload == [
            {
                "title": "summarize",
                "user": "Summarize the latest result.",
                "assistant": "The result has three rows.",
                "records": [],
            }
        ]
    finally:
        pane.stop()


def test_record_card_includes_data_view_meta(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [10, 20]})
    card = render_record_card(
        SimpleNamespace(
            df=df,
            chart_spec=None,
            query=None,
            label="sales",
            record_id="r1",
            query_lexer="sql",
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == [{"kind": "data", "file": card["views"][0]["file"], "meta": "2 rows · 2 columns"}]
