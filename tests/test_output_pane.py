from __future__ import annotations

import json
import urllib.request
from pathlib import Path

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
