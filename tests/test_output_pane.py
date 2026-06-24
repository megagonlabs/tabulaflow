from __future__ import annotations

import json
import urllib.error
import urllib.request
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from tabulaflow.app.render.cards import render_query_html, render_record_card
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


def test_query_view_renders_code_header_and_dracula_theme(tmp_path: Path) -> None:
    path = tmp_path / "query.html"
    render_query_html('print("Hello, world!")', path, lexer="python")

    html = path.read_text()
    assert '<span class="query-lang">Python</span>' in html
    assert 'data-copy-query aria-label="Copy query" title="Copy query"' in html
    assert '<span class="copy-label">Copy</span>' not in html
    assert "#202020" in html
    assert "#8BE9FD" in html  # Dracula builtin/token color.


def test_record_card_links_assets_instead_of_inlining(tmp_path: Path) -> None:
    df = pd.DataFrame({"cat": ["a", "b"], "n": [3, 5]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "cat"}, "y": {"field": "n"}}}
    card = render_record_card(
        SimpleNamespace(df=df, chart_spec=spec, query=None, label="x", record_id="r1", query_lexer="sql"),
        tmp_path,
    )
    assert card is not None
    by_kind = {v["kind"]: tmp_path / v["file"] for v in card["views"]}

    chart_html = by_kind["chart"].read_text()
    assert '<script src="/assets/vega/vega.min.js"></script>' in chart_html
    assert len(chart_html) < 100_000, "Vega should be linked, not inlined (~0.8 MB)"

    data_html = by_kind["data"].read_text()
    assert '<link rel="stylesheet" href="/assets/tabulator/tabulator.min.css">' in data_html
    assert '<script src="/assets/tabulator/tabulator.min.js"></script>' in data_html
    assert len(data_html) < 100_000, "Tabulator should be linked, not inlined (~0.46 MB)"


def test_pane_serves_bundled_assets_cached(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        with urllib.request.urlopen(f"{pane.url}assets/vega/vega-embed.min.js", timeout=2) as resp:
            body = resp.read()
            cache = resp.headers.get("Cache-Control")
        expected = files("tabulaflow.app.assets").joinpath("vega").joinpath("vega-embed.min.js").read_bytes()
        assert body == expected
        assert cache is not None and "immutable" in cache

        try:
            urllib.request.urlopen(f"{pane.url}assets/does-not-exist.js", timeout=2)
            missing_is_404 = False
        except urllib.error.HTTPError as exc:
            missing_is_404 = exc.code == 404
        assert missing_is_404
    finally:
        pane.stop()
