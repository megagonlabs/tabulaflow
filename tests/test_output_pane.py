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


def test_record_card_writes_map_view_payload(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["San Francisco", "Oakland"],
            "latitude": [37.7749, 37.8044],
            "longitude": [-122.4194, -122.2712],
        }
    )
    card = render_record_data(
        SimpleNamespace(
            df=df,
            chart_spec=None,
            map_spec={"lat": "latitude", "lng": "longitude", "label": "city"},
            query=None,
            label="locations",
            record_id="r1",
            query_lexer="sql",
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["map", "data"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["provider"] == "leaflet"
    assert payload["map"]["lat"] == "c1"
    assert payload["map"]["lng"] == "c2"
    assert payload["map"]["label"] == "c0"
    assert payload["map"]["tileUrl"] == "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    assert payload["dataset"]["rows"][0]["c1"] == 37.7749
    assert payload["dataset"]["rows"][0]["c2"] == -122.4194


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
    assert ".turnview.manual-preview { height: calc(100vh - 82px); min-height: 460px;" in _PANE_HTML
    assert f"/assets/pane/pane-render.js?v={renderer_version}" in _PANE_HTML
    assert "__PANE_RENDER_VERSION__" not in _PANE_HTML
    assert "20260630-table-sizing" not in _PANE_HTML


def test_pane_chart_shell_matches_vega_background() -> None:
    assert ".view-shell.view-chart,\n.view-shell.view-map { background: var(--card); }" in _PANE_HTML
    assert ".tf-chart-view,\n.tf-vis-stage { background: var(--card); }" in _PANE_HTML


def test_pane_map_view_is_leaflet_based() -> None:
    renderer = files("tabulaflow.app.assets.pane").joinpath("pane-render.js").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="/assets/leaflet/leaflet.css">' in _PANE_HTML
    assert '<script src="/assets/leaflet/leaflet.js"></script>' in _PANE_HTML
    assert "if (kind === 'map') return TF.renderMap(node, data);" in _PANE_HTML
    assert "function afterVisible(entry)" in _PANE_HTML
    assert "entry.handle.afterVisible" in _PANE_HTML
    assert "renderMap: renderMap" in renderer
    assert "L.map(mapNode" in renderer
    assert "L.tileLayer(String(mapData.tileUrl" in renderer
    assert "L.circleMarker([lat, lng]" in renderer
    assert "map.invalidateSize();" in renderer
    assert ".tf-map-stage { position: relative; height: min(560px, 68vh); min-height: 420px;" in _PANE_HTML


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


def test_pane_manual_tables_use_fixed_panel() -> None:
    renderer = files("tabulaflow.app.assets.pane").joinpath("pane-render.js").read_text(encoding="utf-8")
    assert "container.closest && container.closest('.manual-preview')" in renderer
    assert "container.closest('.view-shell')" in renderer
    assert "panelHeight > 0 ? panelHeight" in renderer
    assert "panelHeight > 0 || rows.length > 100" in renderer
    assert "table.setHeight(height)" in renderer
    assert "requestAnimationFrame(fitFixedPanelHeight)" in renderer
    assert ".turnview.manual-preview { height: calc(100vh - 82px); min-height: 460px;" in _PANE_HTML
    assert ".manual-preview .recordpane { flex: 1 1 auto; min-height: 0;" in _PANE_HTML
    assert ".manual-preview .view-shell { flex: 1 1 auto; min-height: 360px; overflow: hidden; }" in _PANE_HTML
    assert ".manual-preview .tf-table-view,\n.manual-preview .tf-table-wrap { height: 100%;" in _PANE_HTML
    assert ".manual-preview .tf-table-wrap.pane-short { padding-bottom: 0; }" in _PANE_HTML
    assert ".manual-preview .tf-table-view .tabulator { height: 100% !important; }" in _PANE_HTML
    assert "max-height: calc(100% - 38px) !important;" in _PANE_HTML


def test_pane_tables_keep_last_row_gridline() -> None:
    assert (
        ".tabulator-row:last-child .tabulator-cell {\n    border-bottom: 1px solid rgba(58, 67, 82, 0.48);"
        in _PANE_HTML
    )
    assert ".tabulator-row:last-child .tabulator-cell.tabulator-row-header" in _PANE_HTML


def test_pane_view_switches_keep_cached_nodes_mounted() -> None:
    assert "function getCachedRecordData(record)" in _PANE_HTML
    assert "function scheduleIdle(fn)" in _PANE_HTML
    assert "var navState = {};" in _PANE_HTML
    assert "var suppressScrollMemory = false;" in _PANE_HTML
    assert "function getTurnState(turn, index)" in _PANE_HTML
    assert "activeRecord: 0, views: {}, scrollTop: 0" in _PANE_HTML
    assert "state.viewScroll" not in _PANE_HTML
    assert "viewScrollKey" not in _PANE_HTML
    assert "function savedViewKind(state, record, recordIndex, views)" in _PANE_HTML
    assert "function rememberViewKind(state, record, recordIndex, kind)" in _PANE_HTML
    assert "function rememberTurnScroll(state)" in _PANE_HTML
    assert "function restoreTurnScroll(state)" in _PANE_HTML
    assert "function rememberActiveContentScroll()" in _PANE_HTML
    assert "function watchContentScroll()" in _PANE_HTML
    assert "if (suppressScrollMemory) return;" in _PANE_HTML
    assert "scroller.addEventListener('scroll', rememberActiveContentScroll, { passive: true });" in _PANE_HTML
    assert "watchContentScroll();" in _PANE_HTML
    assert "function viewOptionForKind(switcher, kind)" in _PANE_HTML
    assert "opt.dataset.kind = kind;" in _PANE_HTML
    assert "showView(activeKind, viewOptionForKind(switcher, activeKind), true);" in _PANE_HTML
    assert "function buildMultiRecord(records, state)" in _PANE_HTML
    assert "box.appendChild(buildMultiRecord(records, state));" in _PANE_HTML
    assert "state.activeRecord = activeRecord;" in _PANE_HTML
    assert (
        "bar.appendChild(buildRecordTabs(records, activeRecord, function (i) { showRecord(i, false); }));" in _PANE_HTML
    )
    assert "node.toggleAttribute('inert', !active);" in _PANE_HTML
    assert "node.setAttribute('aria-hidden', active ? 'false' : 'true');" in _PANE_HTML
    assert "function stageViewNode(node)" in _PANE_HTML
    assert "function stageShellView(shell, pendingNode)" in _PANE_HTML
    assert "function stageDataView(entry, shell, key, meta)" in _PANE_HTML
    assert "function revealStagedView(shell, key, node)" in _PANE_HTML
    assert "if (kind === 'data') {\n      stageDataView(entry, shell, key, meta);" in _PANE_HTML
    assert "if (node === pendingNode) stageViewNode(node);" in _PANE_HTML
    assert "else hideViewNode(node);" in _PANE_HTML
    assert "function prewarmDataView(record, views, activeKind, shell)" in _PANE_HTML
    assert "function hideViewNode(node)" in _PANE_HTML
    assert "function blurHiddenFocus(node)" in _PANE_HTML
    assert "function syncActiveShellView(shell)" in _PANE_HTML
    assert "function renderHiddenDataView(entry, data)" in _PANE_HTML
    assert "node.setAttribute('inert', '');" in _PANE_HTML
    assert "if (activeKind === 'data' || views.indexOf('data') === -1) return;" in _PANE_HTML
    assert "if (!shell.isConnected || viewCache[key]) return;" in _PANE_HTML
    assert "if (entry.node.parentNode !== shell) shell.appendChild(entry.node);" in _PANE_HTML
    assert "hideViewNode(entry.node);" in _PANE_HTML
    assert "renderHiddenDataView(entry, data);" in _PANE_HTML
    assert "syncActiveShellView(shell);" in _PANE_HTML
    assert "fetchRecordData(record).then(function (data)" in _PANE_HTML
    assert "prewarmDataView(record, views, kind, shell);" in _PANE_HTML
    assert "shell.dataset.activeViewKey = key;" in _PANE_HTML
    assert "if (node.parentNode !== shell) shell.appendChild(node);" in _PANE_HTML
    assert "if (isActiveShellView(shell, key))" in _PANE_HTML
    assert "shell.replaceChildren(entry.node)" not in _PANE_HTML
    assert "shell.replaceChildren(node)" not in _PANE_HTML
    assert "box.replaceChildren(buildRecord" not in _PANE_HTML
    assert "records: records" not in _PANE_HTML
    assert "onSelect: function (i)" not in _PANE_HTML
    assert ".view-shell > .tf-view.view-hidden {" in _PANE_HTML
    assert "opacity: 0;" in _PANE_HTML
    assert ".view-shell > .tf-view.view-pending { position: relative; opacity: 0; pointer-events: none; }" in _PANE_HTML
    assert ".view-shell > .tf-view.view-active { position: relative; opacity: 1; }" in _PANE_HTML


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

        with urllib.request.urlopen(f"{pane.url}assets/leaflet/leaflet.js", timeout=2) as resp:
            assert resp.headers.get("Cache-Control") is not None and "immutable" in resp.headers.get(
                "Cache-Control", ""
            )
            assert b"Leaflet" in resp.read()

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
