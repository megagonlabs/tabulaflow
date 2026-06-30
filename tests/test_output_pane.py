from __future__ import annotations

import contextlib
import hashlib
import json
import socket
import urllib.error
import urllib.request
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tabulaflow.app.render.cards import render_query_html, render_record_data
from tabulaflow.app.pane import OutputPane, OutputPanePortError, _PANE_HTML
from tabulaflow.app.pane_types import PaneRecord, PaneTurn, turn_payload
from tabulaflow.app.screens import send_table_to_output_pane
from tabulaflow.app.tui import TabulaflowApp


@contextlib.contextmanager
def _bound_loopback_port() -> Iterator[int]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    try:
        yield int(sock.getsockname()[1])
    finally:
        sock.close()


def _unused_loopback_port() -> int:
    with _bound_loopback_port() as port:
        return port


def test_output_pane_serves_text_only_turn(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        pane.push(
            turn_payload(
                title="summarize",
                user="Summarize the latest result.",
                assistant="The result has three rows.",
                records=[],
            )
        )

        assert pane.url is not None
        with urllib.request.urlopen(f"{pane.url}events", timeout=2) as response:
            data_line = ""
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_line = line[len("data: ") :]
                    break

        payload = json.loads(data_line)
        assert payload == {
            "id": 0,
            "title": "summarize",
            "user": "Summarize the latest result.",
            "assistant": "The result has three rows.",
            "records": [],
        }
    finally:
        pane.stop()


def test_output_pane_replays_persisted_turns(tmp_path: Path) -> None:
    port = _unused_loopback_port()
    first = OutputPane(tmp_path, port=port)
    first.start()
    try:
        first.push(turn_payload(title="persisted", records=[]))
        manifest = tmp_path / "turns.jsonl"
        assert manifest.exists()
    finally:
        first.stop()

    second = OutputPane(tmp_path, port=port)
    second.start()
    try:
        assert second.url is not None
        with urllib.request.urlopen(f"{second.url}events", timeout=2) as response:
            data_line = ""
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_line = line[len("data: ") :]
                    break

        assert json.loads(data_line) == {"id": 0, "title": "persisted", "records": []}
    finally:
        second.stop()


def test_output_pane_uses_first_available_port_in_range(tmp_path: Path) -> None:
    with _bound_loopback_port() as occupied_port:
        available_port = _unused_loopback_port()
        pane = OutputPane(tmp_path, port_range=(occupied_port, available_port))
        pane.start()
        try:
            assert pane.url == f"http://127.0.0.1:{available_port}/"
        finally:
            pane.stop()


def test_output_pane_explicit_port_is_strict(tmp_path: Path) -> None:
    with _bound_loopback_port() as occupied_port:
        pane = OutputPane(tmp_path, port=occupied_port)
        with pytest.raises(OutputPanePortError, match=str(occupied_port)):
            pane.start()


def test_output_pane_wildcard_bind_uses_loopback_browser_url(tmp_path: Path) -> None:
    available_port = _unused_loopback_port()
    pane = OutputPane(tmp_path, host="0.0.0.0", port=available_port)
    pane.start()
    try:
        assert pane.bind_host == "0.0.0.0"
        assert pane.url == f"http://127.0.0.1:{available_port}/"
        with urllib.request.urlopen(pane.url, timeout=2) as response:
            assert response.status == 200
    finally:
        pane.stop()


def test_output_pane_localhost_bind_uses_loopback_browser_url(tmp_path: Path) -> None:
    available_port = _unused_loopback_port()
    pane = OutputPane(tmp_path, host="localhost", port=available_port)
    pane.start()
    try:
        assert pane.bind_host == "localhost"
        assert pane.url == f"http://127.0.0.1:{available_port}/"
    finally:
        pane.stop()


def test_record_card_includes_data_view_meta(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [10, 20]})
    card = render_record_data(
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
    assert card["views"] == ["data"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["table"]["meta"] == "2 rows · 2 columns"


def test_manual_table_send_includes_data_view_meta(tmp_path: Path) -> None:
    calls: list[tuple[Path, dict[str, object]]] = []
    statuses: list[object] = []

    class FakeApp:
        _runtime_paths = SimpleNamespace(pane_dir=tmp_path)

        def view_record_in_pane(self, record: object, **kwargs: object) -> bool:
            calls.append((Path(f"{record['id']}.data.json"), kwargs))  # type: ignore[index]
            return True

    df = pd.DataFrame({"sample_id": ["ex-0001", "ex-0002"], "answer": ["A", "B"]})
    path = send_table_to_output_pane(df, "manual_table", FakeApp(), status=statuses.append)

    assert path is not None
    assert path.exists()
    payload = json.loads(path.read_text())
    assert payload["table"]["meta"] == "2 rows · 2 columns"
    assert calls == [(Path(path.name), {"title": "manual_table"})]
    assert str(statuses[-1]) == "sent to output pane"


def test_pane_labels_manual_table_turn_as_preview() -> None:
    assert "turn.source === 'manual'" in _PANE_HTML
    assert "return 'table preview';" in _PANE_HTML


def test_pane_omits_text_only_turn_meta() -> None:
    assert "'text only'" not in _PANE_HTML
    assert "metaText ? title.textContent + ' · ' + metaText : title.textContent" in _PANE_HTML


def test_pane_table_renderer_does_not_max_height_short_tables() -> None:
    renderer_path = files("tabulaflow.app.assets.pane").joinpath("pane-render.js")
    renderer = renderer_path.read_text(encoding="utf-8")
    renderer_version = hashlib.sha256(renderer_path.read_bytes()).hexdigest()[:12]
    assert "maxHeight: viewportCap" not in renderer
    assert "estimatedTableHeight > viewportCap" in renderer
    assert "opts.height = viewportCap" in renderer
    assert ".turnview.manual-preview { min-height: calc(100vh - 82px);" in _PANE_HTML
    assert f"/assets/pane/pane-render.js?v={renderer_version}" in _PANE_HTML
    assert "__PANE_RENDER_VERSION__" not in _PANE_HTML
    assert "20260630-table-sizing" not in _PANE_HTML


def test_pane_chart_shell_matches_vega_background() -> None:
    assert ".view-shell.view-chart { background: var(--card); }" in _PANE_HTML
    assert ".tf-chart-view,\n.tf-vis-stage { background: var(--card); }" in _PANE_HTML


def test_pane_table_scrollbars_use_dark_theme() -> None:
    assert "--scrollbar-track: #1a1d23;" in _PANE_HTML
    assert "--scrollbar-thumb: #3a4049;" in _PANE_HTML
    assert "* { scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);" in _PANE_HTML
    assert ".tabulator-tableholder {\n    overscroll-behavior: none;" in _PANE_HTML
    assert "scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);" in _PANE_HTML
    assert "::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb);" in _PANE_HTML


def test_pane_short_tables_keep_bottom_inset() -> None:
    renderer = files("tabulaflow.app.assets.pane").joinpath("pane-render.js").read_text(encoding="utf-8")
    assert "rows.length <= 12 ? 'tf-table-wrap pane-short' : 'tf-table-wrap'" in renderer
    assert ".tf-table-wrap.pane-short { padding-bottom: 16px; box-sizing: border-box; }" in _PANE_HTML


def test_view_record_in_pane_marks_turn_as_manual(tmp_path: Path) -> None:
    pushed: list[PaneTurn] = []

    class FakePane:
        url = "http://127.0.0.1:61111/"

        def push(self, turn: PaneTurn) -> None:
            pushed.append(turn)

    app = TabulaflowApp(model="openai-responses:gpt-5", agent="sql_agent", reasoning_effort="medium")
    app._pane = FakePane()  # type: ignore[assignment]  # noqa: SLF001

    record: PaneRecord = {"id": "rec_orders", "label": None, "views": ["data"]}
    assert app.view_record_in_pane(record, title="orders")
    assert pushed == [
        {
            "title": "orders",
            "source": "manual",
            "records": [{"id": "rec_orders", "label": None, "views": ["data"]}],
        }
    ]


def test_query_view_renders_code_header_and_dracula_theme(tmp_path: Path) -> None:
    path = tmp_path / "query.html"
    render_query_html('print("Hello, world!")', path, lexer="python")

    html = path.read_text()
    assert '<span class="query-lang">Python</span>' in html
    assert 'data-copy-query aria-label="Copy query" title="Copy query"' in html
    assert '<span class="copy-label">Copy</span>' not in html
    assert "#1e1e1e" in html
    assert "#303030" in html
    assert "#8BE9FD" in html  # Dracula builtin/token color.


def test_record_card_writes_structured_data_instead_of_html(tmp_path: Path) -> None:
    df = pd.DataFrame({"cat": ["a", "b"], "n": [3, 5]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "cat"}, "y": {"field": "n"}}}
    card = render_record_data(
        SimpleNamespace(df=df, chart_spec=spec, query=None, label="x", record_id="r1", query_lexer="sql"),
        tmp_path,
    )
    assert card is not None
    assert card["views"] == ["chart", "data"]
    payload_path = tmp_path / f"{card['id']}.data.json"
    payload = json.loads(payload_path.read_text())
    assert set(payload) == {"dataset", "table", "chart"}
    assert payload["dataset"]["rows"] == [{"c0": "a", "c1": 3}, {"c0": "b", "c1": 5}]
    assert payload["chart"]["spec"]["encoding"]["x"] == {"field": "c0", "title": "cat"}
    assert payload_path.stat().st_size < 100_000


def test_pane_serves_bundled_assets_cached(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        with urllib.request.urlopen(pane.url, timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"

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

        with urllib.request.urlopen(f"{pane.url}assets/pane/pane-render.js", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") == "no-cache"
            assert b"renderTable" in resp.read()
    finally:
        pane.stop()
