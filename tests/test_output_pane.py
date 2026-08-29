from __future__ import annotations

import contextlib
import asyncio
import json
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from tabulaflow.app.config import LLM_OFF, ResolvedLLMSelection
from tabulaflow.app.pane.graphs import build_graph_result_data
from tabulaflow.app.pane.cards import (
    MapCardInput,
    ResultCardInput,
    build_query_data,
    render_map_data,
    render_resolved_output,
    render_result_data,
)
from tabulaflow.app.pane.contract import CARD_ID_PREFIX, PaneCard, PanePanel, PaneTurn, turn_payload
from tabulaflow.app.pane.server import OutputPane, OutputPanePortError
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.output.graphs import materialize_graph_result, normalize_graph_spec
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.turn import TurnOutput
from tabulaflow.agents.chat import ChatResult
from tabulaflow.core import GraphResult
from tabulaflow.output.specs import (
    ChoiceOption,
    ChoiceParameter,
    FixedResultSource,
    OutputSpec,
    TableArtifactSpec,
)
from tabulaflow.output.store import OutputStore, ResultMetadata, ResultPayload
from tabulaflow.output.resolver import ResolvedOutput, ResolvedTableArtifact, UnavailableArtifact


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


def _origin_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))


def _runtime_paths(root: Path) -> RuntimePaths:
    return RuntimePaths.for_session("test-session", home_dir=root)


def test_output_pane_serves_text_only_turn(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        pane.push(
            turn_payload(
                title="summarize",
                user="Summarize the latest result.",
                assistant="The result has three rows.",
                cards=[],
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
            "cards": [],
        }
    finally:
        pane.stop()


def test_output_pane_replays_only_missed_turns(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        pane.push(turn_payload(title="first", cards=[]))
        pane.push(turn_payload(title="second", cards=[]))

        assert pane.url is not None
        request = urllib.request.Request(f"{pane.url}events", headers={"Last-Event-ID": "0"})
        with urllib.request.urlopen(request, timeout=2) as response:
            data_line = ""
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_line = line[len("data: ") :]
                    break

        assert json.loads(data_line) == {"id": 1, "title": "second", "cards": []}
    finally:
        pane.stop()


def test_output_pane_uses_first_available_port_in_range(tmp_path: Path) -> None:
    with _bound_loopback_port() as occupied_port:
        available_port = _unused_loopback_port()
        pane = OutputPane(tmp_path, port_range=(occupied_port, available_port))
        pane.start()
        try:
            assert pane.url == f"http://127.0.0.1:{available_port}/{pane.token}/"
        finally:
            pane.stop()


def test_output_pane_default_token_is_48_bits(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)

    assert len(pane.token) == 8


def test_output_pane_fallback_session_id_uses_cli_format(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)

    assert re.fullmatch(r"[0-9a-z]{6}", pane.session_id)


def test_output_pane_page_displays_runtime_session_id(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path, session_id="k3x9qe")
    assert pane.session_id == "k3x9qe"

    pane.start()
    try:
        assert pane.url is not None
        with urllib.request.urlopen(pane.url, timeout=2) as response:
            body = response.read().decode("utf-8")

        assert '<span id="session-id" title="Session id">session <code>k3x9qe</code></span>' in body
        assert pane.token not in body
        assert "__SESSION_ID__" not in body
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
        assert pane.url == f"http://127.0.0.1:{available_port}/{pane.token}/"
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
        assert pane.url == f"http://127.0.0.1:{available_port}/{pane.token}/"
    finally:
        pane.stop()


def test_output_pane_public_url_gets_token_path(tmp_path: Path) -> None:
    available_port = _unused_loopback_port()
    pane = OutputPane(tmp_path, port=available_port, public_url=f"http://127.0.0.1:{available_port}/tf")
    pane.start()
    try:
        assert pane.url == f"http://127.0.0.1:{available_port}/tf/{pane.token}/"
        with urllib.request.urlopen(pane.url, timeout=2) as response:
            assert response.status == 200
    finally:
        pane.stop()


def test_output_pane_rejects_missing_or_wrong_token(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        origin = _origin_url(pane.url)
        for path in ("", "events", "wrong/events"):
            try:
                urllib.request.urlopen(f"{origin}{path}", timeout=2)
                rejected = False
            except urllib.error.HTTPError as exc:
                rejected = exc.code == 404
                body = exc.read().decode("utf-8")
            assert rejected
            assert "Output pane URL is incomplete." in body
            assert "Open the full URL shown in the tabulaflow terminal." in body
            assert pane.token not in body
    finally:
        pane.stop()


def test_result_card_includes_data_view_meta(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["North", "South"], "revenue": [10, 20]})
    card = render_result_data(
        ResultCardInput(
            df=df,
            label="sales",
            chart_spec=None,
            query=None,
            query_lexer="sql",
        ),
        tmp_path,
    )

    assert card is not None
    assert card["views"] == ["data"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["table"]["meta"] == "2 rows · 2 columns"
    assert payload["table"]["columns"][1]["role"] == "number"
    assert payload["dataset"]["rows"][0]["c1"] == 10


def test_result_card_preserves_null_cells(tmp_path: Path) -> None:
    df = pd.DataFrame({"name": ["valid", None], "score": [0.019593312555829002, None]})
    card = render_result_data(
        ResultCardInput(
            df=df,
            label="nulls",
            chart_spec=None,
            query=None,
            query_lexer="sql",
        ),
        tmp_path,
    )

    assert card is not None
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["dataset"]["rows"][1] == {"c0": None, "c1": None}
    assert payload["table"]["columns"][1]["role"] == "number"


def test_result_card_renders_empty_dataframe_as_data_view(tmp_path: Path) -> None:
    df = pd.DataFrame({"customer": pd.Series(dtype="object"), "value": pd.Series(dtype="int64")})
    card = render_result_data(ResultCardInput(df=df, label="empty", query="SELECT customer, value FROM t"), tmp_path)

    assert card is not None
    assert card["views"] == ["data", "query"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["dataset"]["rows"] == []
    assert payload["table"]["meta"] == "0 rows · 2 columns"


def test_empty_chart_result_keeps_chart_and_data_views(tmp_path: Path) -> None:
    df = pd.DataFrame({"customer": pd.Series(dtype="object"), "value": pd.Series(dtype="int64")})
    spec = {"mark": "bar", "encoding": {"x": {"field": "customer"}, "y": {"field": "value"}}}
    card = render_result_data(ResultCardInput(df=df, label="empty chart", chart_spec=spec), tmp_path)

    assert card is not None
    assert card["views"] == ["chart", "data"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["chart"]["spec"]["mark"] == "bar"
    assert payload["table"]["meta"] == "0 rows · 2 columns"


def _map_card(
    map_spec: dict[str, object],
    sources: dict[str, pd.DataFrame],
    tmp_path: Path,
    *,
    label: str = "map",
) -> PaneCard:
    card = render_map_data(MapCardInput(label=label, spec=map_spec, sources=sources), tmp_path)
    assert card is not None
    assert card["id"].startswith(CARD_ID_PREFIX)
    return card


def test_map_card_writes_points_payload(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["San Francisco", "Oakland"],
            "latitude": [37.7749, 37.8044],
            "longitude": [-122.4194, -122.2712],
        }
    )
    card = _map_card(
        {"layers": [{"type": "points", "source_id": "Q1", "lat": "latitude", "lng": "longitude", "label": "city"}]},
        {"Q1": df},
        tmp_path,
        label="locations",
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["provider"] == "maplibre"
    assert payload["map"]["layers"] == [
        {"type": "points", "source": "Q1", "lat": "c1", "lng": "c2", "label": "c0"},
    ]
    assert "tileUrl" not in payload["map"]
    assert payload["datasets"]["Q1"]["rows"][0]["c1"] == 37.7749
    assert payload["datasets"]["Q1"]["rows"][0]["c2"] == -122.4194


def test_map_card_preserves_blank_coordinate_strings_for_map_renderer(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["Missing", "San Francisco"],
            "latitude": ["", "37.7749"],
            "longitude": ["", "-122.4194"],
        }
    )
    card = _map_card(
        {"layers": [{"type": "points", "source_id": "Q1", "lat": "latitude", "lng": "longitude", "label": "city"}]},
        {"Q1": df},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["datasets"]["Q1"]["rows"][0]["c1"] == ""
    assert payload["datasets"]["Q1"]["rows"][0]["c2"] == ""


def test_map_card_preserves_size_domain_and_circle_marker(tmp_path: Path) -> None:
    df = pd.DataFrame({"lat": [1.0], "lng": [2.0], "value": [50]})
    card = _map_card(
        {
            "layers": [
                {
                    "type": "points",
                    "source_id": "Q1",
                    "lat": "lat",
                    "lng": "lng",
                    "size": {"field": "value", "domain": [0, 100]},
                    "marker": {"type": "circle"},
                }
            ]
        },
        {"Q1": df},
        tmp_path,
    )

    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["size"] == {"field": "c2", "domain": [0, 100]}
    assert payload["map"]["layers"][0]["marker"] == {"type": "circle"}


def test_map_card_writes_layered_single_source_payload(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "city": ["San Francisco"],
            "latitude": [37.7749],
            "longitude": [-122.4194],
            "region": ["Bay Area"],
            "category": ["urban"],
            "boundary_geojson": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-122.52, 37.70],
                                [-122.35, 37.70],
                                [-122.35, 37.84],
                                [-122.52, 37.84],
                                [-122.52, 37.70],
                            ]
                        ],
                    },
                    "properties": {"kind": "region"},
                }
            ],
        }
    )
    card = _map_card(
        {
            "layers": [
                {
                    "type": "geojson",
                    "source_id": "Q1",
                    "geojson": "boundary_geojson",
                    "label": "region",
                    "tooltip": ["category"],
                    "color": {"field": "region"},
                },
                {
                    "type": "points",
                    "source_id": "Q1",
                    "lat": "latitude",
                    "lng": "longitude",
                    "label": "city",
                    "tooltip": ["category"],
                },
            ]
        },
        {"Q1": df},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["type"] == "geojson"
    assert payload["map"]["layers"][0]["source"] == "Q1"
    assert payload["map"]["layers"][0]["geojson"] == "c5"
    assert payload["map"]["layers"][0]["label"] == "c3"
    assert payload["map"]["layers"][0]["tooltip"] == ["c4"]
    assert payload["map"]["layers"][0]["color"] == {"field": "c3"}
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "source": "Q1",
        "lat": "c1",
        "lng": "c2",
        "label": "c0",
        "tooltip": ["c4"],
    }


def test_map_card_writes_multi_source_datasets(tmp_path: Path) -> None:
    boundaries = pd.DataFrame(
        {
            "area": ["Bay Area"],
            "boundary_geojson": [{"type": "Point", "coordinates": [-122.4, 37.7]}],
        }
    )
    points = pd.DataFrame({"city": ["San Francisco"], "latitude": [37.7749], "longitude": [-122.4194]})
    card = _map_card(
        {
            "layers": [
                {"type": "geojson", "source_id": "Q1", "geojson": "boundary_geojson", "label": "area"},
                {"type": "points", "source_id": "Q2", "lat": "latitude", "lng": "longitude", "label": "city"},
            ]
        },
        {"Q1": boundaries, "Q2": points},
        tmp_path,
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    # Each layer reads from its own source's compact field names.
    assert payload["map"]["layers"][0] == {"type": "geojson", "source": "Q1", "geojson": "c1", "label": "c0"}
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "source": "Q2",
        "lat": "c1",
        "lng": "c2",
        "label": "c0",
    }
    assert set(payload["datasets"]) == {"Q1", "Q2"}
    assert payload["datasets"]["Q2"]["rows"][0]["c1"] == 37.7749


def test_map_card_writes_inline_point_layer(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "route_geojson": [
                {
                    "type": "LineString",
                    "coordinates": [[-122.42, 37.77], [-122.27, 37.80]],
                }
            ],
            "route_name": ["Route"],
        }
    )
    card = _map_card(
        {
            "layers": [
                {"type": "geojson", "source_id": "Q1", "geojson": "route_geojson", "label": "route_name"},
                {
                    "type": "points",
                    "points": [{"lat": 37.8044, "lng": -122.2712, "label": "Destination", "kind": "destination"}],
                    "label": "label",
                    "tooltip": ["kind"],
                },
            ]
        },
        {"Q1": df},
        tmp_path,
        label="route",
    )

    assert card["views"] == ["map"]
    payload = json.loads((tmp_path / f"{card['id']}.data.json").read_text())
    assert payload["map"]["layers"][0]["geojson"] == "c0"
    assert payload["map"]["layers"][0]["label"] == "c1"
    assert payload["map"]["layers"][1] == {
        "type": "points",
        "points": [{"lat": 37.8044, "lng": -122.2712, "label": "Destination", "kind": "destination"}],
        "label": "label",
        "tooltip": ["kind"],
    }


def test_manual_table_send_includes_data_view_meta(tmp_path: Path) -> None:
    pushed: list[PaneTurn] = []

    class FakePane:
        url = "http://127.0.0.1:61111/"

        def push(self, turn: PaneTurn) -> None:
            pushed.append(turn)

    df = pd.DataFrame({"sample_id": ["ex-0001", "ex-0002"], "answer": ["A", "B"]})
    runtime_paths = _runtime_paths(tmp_path)
    app = TabulaflowApp(
        llm_selection=ResolvedLLMSelection(LLM_OFF, None),
        runtime_paths=runtime_paths,
        project_dir=tmp_path,
    )
    app._pane = FakePane()  # type: ignore[assignment]  # noqa: SLF001

    assert app.show_table_in_pane(df, title="manual_table")

    path = next(runtime_paths.pane_dir.glob("card_*.data.json"))
    payload = json.loads(path.read_text())
    assert payload["table"]["meta"] == "2 rows · 2 columns"
    assert pushed[0]["title"] == "manual_table"
    assert pushed[0]["source"] == "manual"


def test_pane_markdown_renderer_formats_safe_markdown(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute the browser markdown renderer")

    assets = files("tabulaflow.app.pane.assets")
    vendor_path = str(assets.joinpath("vendor").joinpath("markdown-it").joinpath("markdown-it.min.js"))
    renderer_assets = assets.joinpath("ui").joinpath("render")
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    for rel in ("shared.js", "code.js", "markdown.js"):
        module_dir.joinpath(rel).write_text(renderer_assets.joinpath(rel).read_text(encoding="utf-8"), encoding="utf-8")
    module_dir.joinpath("package.json").write_text('{"type":"module"}', encoding="utf-8")
    renderer_path = str(module_dir / "markdown.js")
    markdown = """# Heading

**bold** and https://example.com

| A | B |
|---|---|
| 1 | 2 |

<script>alert(1)</script>

![alt](https://example.com/image.png)

![](https://example.com/path/to/fallback-image.png)

[![linked alt](https://example.com/linked.png)](https://example.com/page)

![collapsed][]

[collapsed]: https://example.com/collapsed.png

![shortcut]

[shortcut]: https://example.com/shortcut.png

[unsafe](javascript:alert(1))
"""
    script = f"""
import fs from 'node:fs';
import vm from 'node:vm';
import {{ pathToFileURL }} from 'node:url';
const sandbox = {{}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync({json.dumps(vendor_path)}, 'utf8'), sandbox);
globalThis.window = {{ markdownit: sandbox.markdownit }};
const moduleUrl = pathToFileURL({json.dumps(renderer_path)}).href;
const {{ renderMarkdown }} = await import(moduleUrl);
const classes = [];
const attrs = {{}};
const link = {{ setAttribute: (name, value) => {{ attrs[name] = value; }} }};
const target = {{
  classList: {{ add: (value) => {{ classes.push(value); }} }},
  innerHTML: '',
  textContent: '',
  querySelectorAll: (selector) => selector === 'a[href]' ? [link] : [],
}};
renderMarkdown(target, {json.dumps(markdown)});
process.stdout.write(JSON.stringify({{ classes, attrs, html: target.innerHTML }}));
"""
    result = subprocess.run(
        [node, "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )
    rendered = json.loads(result.stdout)

    assert rendered["classes"] == ["md"]
    assert rendered["attrs"] == {"target": "_blank", "rel": "noopener noreferrer"}
    assert "<h1>Heading</h1>" in rendered["html"]
    assert "<strong>bold</strong>" in rendered["html"]
    assert "<table>" in rendered["html"]
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered["html"]
    assert (
        '<a class="md-image-ref" href="https://example.com/image.png" '
        'title="https://example.com/image.png" aria-label="Open image: alt">'
    ) in rendered["html"]
    assert '<span class="md-image-icon">' in rendered["html"]
    assert '<span class="md-image-label">alt</span>' in rendered["html"]
    assert '<span class="md-image-label">example.com/path/to/fallback-image.png</span>' in rendered["html"]
    assert '<span class="md-image-label">collapsed</span>' in rendered["html"]
    assert '<span class="md-image-label">shortcut</span>' in rendered["html"]
    assert 'href="https://example.com/collapsed.png"' in rendered["html"]
    assert 'href="https://example.com/shortcut.png"' in rendered["html"]
    assert "md-image-src" not in rendered["html"]
    assert (
        '<a href="https://example.com/page"><span class="md-image-ref md-image-ref-nested" '
        'title="https://example.com/linked.png">'
    ) in rendered["html"]
    assert 'href="https://example.com/linked.png"' not in rendered["html"]
    assert "!<a" not in rendered["html"]
    assert "<img" not in rendered["html"]
    assert 'href="javascript:' not in rendered["html"]


def test_pane_markdown_renderer_formats_latex_math(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute the browser markdown renderer")

    assets = files("tabulaflow.app.pane.assets")
    markdown_it_path = str(assets.joinpath("vendor").joinpath("markdown-it").joinpath("markdown-it.min.js"))
    katex_path = str(assets.joinpath("vendor").joinpath("katex").joinpath("katex.min.js"))
    texmath_path = str(assets.joinpath("vendor").joinpath("markdown-it-texmath").joinpath("texmath.js"))
    renderer_assets = assets.joinpath("ui").joinpath("render")
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    for rel in ("shared.js", "code.js", "markdown.js"):
        module_dir.joinpath(rel).write_text(renderer_assets.joinpath(rel).read_text(encoding="utf-8"), encoding="utf-8")
    module_dir.joinpath("package.json").write_text('{"type":"module"}', encoding="utf-8")
    renderer_path = str(module_dir / "markdown.js")
    markdown = r"""Inline \(x^2 + y^2\).

\[
\frac{a}{b}
\]

Price stays literal: $100 and $200.
"""
    script = f"""
import fs from 'node:fs';
import vm from 'node:vm';
import {{ pathToFileURL }} from 'node:url';
const sandbox = {{}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync({json.dumps(markdown_it_path)}, 'utf8'), sandbox);
vm.runInContext(fs.readFileSync({json.dumps(katex_path)}, 'utf8'), sandbox);
vm.runInContext(fs.readFileSync({json.dumps(texmath_path)}, 'utf8'), sandbox);
globalThis.window = {{
  markdownit: sandbox.markdownit,
  katex: sandbox.katex,
  texmath: sandbox.texmath
}};
const moduleUrl = pathToFileURL({json.dumps(renderer_path)}).href;
const {{ renderMarkdown }} = await import(moduleUrl);
const classes = [];
const target = {{
  classList: {{ add: (value) => {{ classes.push(value); }} }},
  innerHTML: '',
  textContent: '',
  querySelectorAll: () => [],
}};
renderMarkdown(target, {json.dumps(markdown)});
process.stdout.write(JSON.stringify({{ classes, html: target.innerHTML }}));
"""
    result = subprocess.run(
        [node, "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )
    rendered = json.loads(result.stdout)

    assert rendered["classes"] == ["md"]
    assert '<span class="katex">' in rendered["html"]
    assert '<eq><span class="katex">' in rendered["html"]
    assert '<eqn><span class="katex-display">' in rendered["html"]
    assert "Price stays literal: $100 and $200." in rendered["html"]


def test_pane_code_copy_button_shows_copied_feedback(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute the browser code renderer")

    assets = files("tabulaflow.app.pane.assets").joinpath("ui").joinpath("render")
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    for rel in ("shared.js", "code.js"):
        module_dir.joinpath(rel).write_text(assets.joinpath(rel).read_text(encoding="utf-8"), encoding="utf-8")
    module_dir.joinpath("package.json").write_text('{"type":"module"}', encoding="utf-8")
    renderer_path = str(module_dir / "code.js")
    script = f"""
import {{ pathToFileURL }} from 'node:url';
const moduleUrl = pathToFileURL({json.dumps(renderer_path)}).href;
const timers = [];
globalThis.window = {{ setTimeout: (callback, ms) => {{ timers.push({{ callback, ms }}); return timers.length; }},
                       clearTimeout: () => {{}} }};
Object.defineProperty(globalThis, 'navigator', {{
  value: {{ clipboard: {{ writeText: (text) => Promise.resolve(text) }} }},
  configurable: true,
}});
const buttonClasses = new Set();
const button = {{
  classList: {{
    toggle: (name, on) => on ? buttonClasses.add(name) : buttonClasses.delete(name),
    remove: (...names) => names.forEach((name) => buttonClasses.delete(name)),
  }},
  attrs: {{}},
  title: '',
  setAttribute: function (name, value) {{ this.attrs[name] = value; }},
  addEventListener: function (event, callback) {{ this.click = callback; }},
}};
const container = {{
  _html: '',
  set innerHTML(value) {{ this._html = value; }},
  get innerHTML() {{ return this._html; }},
  querySelector: (selector) => selector === '[data-copy-code]' ? button : null,
}};
const {{ renderCodeCard }} = await import(moduleUrl);
renderCodeCard(container, {{ code: 'select 1', lexer: 'sql', language: 'SQL', html: '<div class="highlight"><pre>select 1</pre></div>' }},
  {{ copyLabel: 'Copy query', copiedLabel: 'Copied query' }});
await button.click();
const copied = {{ classes: [...buttonClasses].sort(), label: button.attrs['aria-label'], title: button.title, timerMs: timers[0].ms }};
timers[0].callback();
const reset = {{ classes: [...buttonClasses].sort(), label: button.attrs['aria-label'], title: button.title }};
process.stdout.write(JSON.stringify({{ html: container.innerHTML, copied, reset }}));
"""
    result = subprocess.run(
        [node, "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )
    rendered = json.loads(result.stdout)

    assert 'data-copy-code aria-label="Copy query" title="Copy query"' in rendered["html"]
    assert rendered["copied"] == {"classes": ["copied"], "label": "Copied query", "title": "Copied", "timerMs": 1200}
    assert rendered["reset"] == {"classes": [], "label": "Copy query", "title": "Copy query"}


def test_table_copy_serializes_complete_values_as_tsv(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute the table renderer")

    assets = files("tabulaflow.app.pane.assets").joinpath("ui").joinpath("render")
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    for rel in ("shared.js", "table.js"):
        module_dir.joinpath(rel).write_text(assets.joinpath(rel).read_text(encoding="utf-8"), encoding="utf-8")
    module_dir.joinpath("package.json").write_text('{"type":"module"}', encoding="utf-8")
    renderer_path = str(module_dir / "table.js")
    script = f"""
import {{ pathToFileURL }} from 'node:url';
globalThis.window = {{ Tabulator: {{}} }};
const moduleUrl = pathToFileURL({json.dumps(renderer_path)}).href;
const {{ tableToTsv }} = await import(moduleUrl);
const columns = [
  {{ title: 'Name', field: 'name' }},
  {{ title: 'Notes', field: 'notes' }},
  {{ title: 'Meta', field: 'meta' }},
  {{ title: 'Media', field: 'media' }},
];
const rows = [
  {{ name: 'Alice', notes: 'one\\ttwo', meta: {{ a: 1 }}, media: {{ kind: 'media', src: 'https://example.com/a.png' }} }},
  {{ name: 'Bob', notes: 'line\\n"quoted"', meta: null, media: null }},
];
process.stdout.write(JSON.stringify(tableToTsv(columns, rows)));
"""
    result = subprocess.run(
        [node, "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )

    assert json.loads(result.stdout) == (
        "Name\tNotes\tMeta\tMedia\n"
        'Alice\t"one\ttwo"\t"{""a"":1}"\thttps://example.com/a.png\n'
        'Bob\t"line\n""quoted"""\t\t'
    )


def test_output_pane_push_highlights_assistant_markdown_code_blocks(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.push(
        turn_payload(
            title="code",
            cards=[],
            assistant="Before\n\n```python\nprint('hi')\n```\n\n```\nplain\n```",
        )
    )

    turn = pane._wait_for_turns(-1, timeout=0)[0]  # noqa: SLF001
    blocks = turn["assistantCodeBlocks"]
    assert blocks[0]["code"] == "print('hi')\n"
    assert [block["lexer"] for block in blocks] == ["python", "text"]
    assert blocks[0]["language"] == "Python"
    assert "print" in blocks[0]["html"]
    assert "#E0E0E0" in blocks[0]["html"]


def test_graph_tooltips_preserve_nested_values() -> None:
    spec = {
        "nodes": [
            {
                "data": [
                    {"id": "a", "label": "Alice", "tags": ["lead"], "profile": {"city": "Oakland"}},
                    {"id": "b", "label": "Bob"},
                ],
                "id": "id",
                "label": "label",
                "tooltip": True,
            }
        ],
        "edges": [
            {
                "data": [
                    {
                        "src": "a",
                        "dst": "b",
                        "rel": "knows",
                        "roles": ["mentor", "reviewer"],
                        "metadata": {"since": 2024},
                    }
                ],
                "source": "src",
                "target": "dst",
                "label": "rel",
                "tooltip": True,
            }
        ],
    }
    normalized = normalize_graph_spec(spec, {})
    payload = build_graph_result_data(materialize_graph_result(normalized, {}))
    assert payload is not None
    # Element dicts hold ``object`` values; the test asserts on their nested shape.
    nodes = cast("list[dict[str, Any]]", payload["graph"]["elements"]["nodes"])
    edges = cast("list[dict[str, Any]]", payload["graph"]["elements"]["edges"])
    alice = next(node["data"] for node in nodes if node["data"]["id"] == "a")
    assert alice["properties"]["tags"] == ["lead"]
    assert alice["properties"]["profile"] == {"city": "Oakland"}
    assert edges[0]["data"]["properties"]["roles"] == ["mentor", "reviewer"]
    assert edges[0]["data"]["properties"]["metadata"] == {"since": 2024}


def test_graph_constant_group_colors_and_edge_label() -> None:
    spec = {
        "nodes": [
            {"data": [{"id": "a"}], "id": "id", "group": {"value": "Customer"}},
            {"data": [{"id": "p"}], "id": "id", "group": {"value": "Product"}},
        ],
        "edges": [
            {
                "data": [{"src": "a", "dst": "p"}],
                "source": "src",
                "target": "dst",
                "label": {"value": "PURCHASED"},
            }
        ],
    }
    normalized = normalize_graph_spec(spec, {})
    payload = build_graph_result_data(materialize_graph_result(normalized, {}))
    assert payload is not None
    nodes = cast("list[dict[str, Any]]", payload["graph"]["elements"]["nodes"])
    edges = cast("list[dict[str, Any]]", payload["graph"]["elements"]["edges"])
    by_id = {node["data"]["id"]: node["data"] for node in nodes}
    assert by_id["a"]["group"] == "Customer"
    assert by_id["p"]["group"] == "Product"
    assert by_id["a"]["color"] != by_id["p"]["color"]
    assert edges[0]["data"]["label"] == "PURCHASED"


def test_empty_graph_builds_a_normal_graph_payload() -> None:
    payload = build_graph_result_data(GraphResult(nodes=[], edges=[]))

    assert payload is not None
    assert payload["graph"]["elements"] == {"nodes": [], "edges": []}


async def test_unavailable_artifact_renders_message_view(tmp_path: Path) -> None:
    resolved = ResolvedOutput(
        selection={},
        artifacts=[
            UnavailableArtifact(
                artifact_id="S1", label="detail", reason="Only applies to revenue", status="not_applicable"
            )
        ],
    )

    cards = await render_resolved_output(resolved, tmp_path)

    assert cards == [{"id": cards[0]["id"], "artifact_id": "S1", "label": "detail", "views": ["message"]}]
    payload = json.loads((tmp_path / f"{cards[0]['id']}.data.json").read_text())
    assert payload == {"message": {"status": "not_applicable", "text": "Only applies to revenue"}}


async def test_error_artifact_renders_error_message_view(tmp_path: Path) -> None:
    resolved = ResolvedOutput(
        selection={},
        artifacts=[UnavailableArtifact(artifact_id="S1", label="detail", reason="boom", status="error")],
    )

    cards = await render_resolved_output(resolved, tmp_path)

    payload = json.loads((tmp_path / f"{cards[0]['id']}.data.json").read_text())
    assert cards[0]["views"] == ["message"]
    assert payload == {"message": {"status": "error", "text": "boom"}}


async def test_no_result_artifact_renders_info_message_view(tmp_path: Path) -> None:
    resolved = ResolvedOutput(
        selection={},
        artifacts=[UnavailableArtifact(artifact_id="S1", label="detail", reason="No result set", status="no_result")],
    )

    cards = await render_resolved_output(resolved, tmp_path)

    payload = json.loads((tmp_path / f"{cards[0]['id']}.data.json").read_text())
    assert cards[0]["views"] == ["message"]
    assert payload == {"message": {"status": "no_result", "text": "No result set"}}


async def test_pane_preparation_failure_renders_safe_error_card(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import tabulaflow.app.pane.cards as pane_cards

    artifact = ResolvedTableArtifact(
        artifact_id="S1",
        source_id="S1",
        label="orders",
        payload=ResultPayload(
            metadata=ResultMetadata(id="R1", db_alias="workspace", query="SELECT * FROM orders"),
            df=pd.DataFrame({"id": [1]}),
        ),
    )

    def fail_render(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("internal detail")

    monkeypatch.setattr(pane_cards, "render_result_data", fail_render)

    cards = await render_resolved_output(ResolvedOutput(selection={}, artifacts=[artifact]), tmp_path)

    assert cards == [{"id": cards[0]["id"], "artifact_id": "S1", "label": "orders", "views": ["message"]}]
    payload = json.loads((tmp_path / f"{cards[0]['id']}.data.json").read_text())
    assert payload == {"message": {"status": "error", "text": "Could not prepare this artifact for display."}}
    assert "preparing pane card for artifact S1 failed" in caplog.text
    assert "internal detail" not in payload["message"]["text"]


def test_live_view_survives_replay_and_view_switching(tmp_path: Path) -> None:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    df = pd.DataFrame({"cat": ["a", "b"], "n": [3, 5]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "cat"}, "y": {"field": "n"}}}
    cards: list[PaneCard] = []
    for index in range(27):
        card = render_result_data(ResultCardInput(df=df, label=f"chart_{index}", chart_spec=spec), tmp_path)
        assert card is not None
        cards.append(card)

    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except PlaywrightError as exc:
                pytest.skip(f"Playwright Chromium is unavailable: {exc}")
            try:
                page = browser.new_page(viewport={"width": 1200, "height": 900})
                page.goto(pane.url, wait_until="domcontentloaded")
                for index, card in enumerate(cards):
                    pane.push(turn_payload(title=f"replay {index}", cards=[card]))
                pane.push(turn_payload(title="reused card", cards=[cards[0]]))

                page.wait_for_function(
                    "document.querySelector('.turnitem.active .turntitle')?.textContent === 'reused card'"
                )
                page.wait_for_selector(".view-shell .view-active.tf-chart-view svg")
                page.locator(".seg-opt[data-kind='data']").click()
                page.wait_for_selector(".view-shell .view-active.tf-table-view")
                assert page.locator(".view-shell").get_attribute("aria-busy") is None

                page.locator(".turnitem").nth(1).click()
                page.wait_for_function(
                    "document.querySelector('.turnitem.active .turntitle')?.textContent === 'replay 1'"
                )
                page.wait_for_selector(".view-shell .view-active.tf-chart-view svg")
            finally:
                browser.close()
    finally:
        pane.stop()


def test_map_style_is_structurally_valid() -> None:
    assets = files("tabulaflow.app.pane.assets").joinpath("vendor", "maplibre")
    style = json.loads(assets.joinpath("shortbread-light.json").read_text(encoding="utf-8"))

    layer_ids = [layer["id"] for layer in style["layers"]]
    assert len(layer_ids) == len(set(layer_ids))
    assert all(layer.get("source") in style["sources"] for layer in style["layers"] if "source" in layer)
    assert style["sources"]["osm"]["url"] == "https://vector.openstreetmap.org/shortbread_v1/tilejson.json"
    assert "OpenStreetMap contributors" in style["sources"]["osm"]["attribution"]

    local_urls = [
        source["data"]
        for source in style["sources"].values()
        if isinstance(source, dict) and isinstance(source.get("data"), str) and source["data"].startswith("/assets/")
    ]
    for url in local_urls:
        relative = url.removeprefix("/assets/vendor/maplibre/")
        assert assets.joinpath(relative).is_file()

    for sprite in style["sprite"]:
        stem = sprite["url"]
        assert assets.joinpath(f"{stem}.json").is_file()
        assert assets.joinpath(f"{stem}.png").is_file()
        assert assets.joinpath(f"{stem}@2x.json").is_file()
        assert assets.joinpath(f"{stem}@2x.png").is_file()


def test_view_card_in_pane_marks_turn_as_manual(tmp_path: Path) -> None:
    pushed: list[PaneTurn] = []

    class FakePane:
        url = "http://127.0.0.1:61111/"

        def push(self, turn: PaneTurn) -> None:
            pushed.append(turn)

    app = TabulaflowApp(
        llm_selection=ResolvedLLMSelection(LLM_OFF, None),
        runtime_paths=_runtime_paths(tmp_path),
        project_dir=tmp_path,
    )
    app._pane = FakePane()  # type: ignore[assignment]  # noqa: SLF001

    card: PaneCard = {"id": "card_orders", "artifact_id": "orders", "label": None, "views": ["data"]}
    assert app.view_card_in_pane(card, title="orders")
    assert pushed == [
        {
            "title": "orders",
            "source": "manual",
            "cards": [{"id": "card_orders", "artifact_id": "orders", "label": None, "views": ["data"]}],
        }
    ]


async def test_output_pane_resolves_live_turn_selection(tmp_path: Path) -> None:
    class FakeOutputStore:
        async def get_payload(self, result_id: str) -> ResultPayload:
            return ResultPayload(
                metadata=ResultMetadata(id=result_id, db_alias="workspace", query="SELECT 1"),
                df=pd.DataFrame({"period": ["q3"]}),
            )

    pane = OutputPane(tmp_path)
    result = ChatResult(
        text="x",
        output=OutputSpec(
            parameters=[
                ChoiceParameter(
                    id="period",
                    label="Period",
                    choices=[ChoiceOption(id="q2", label="Q2"), ChoiceOption(id="q3", label="Q3")],
                )
            ],
            sources=[FixedResultSource(id="period_q3", result_id="Q1")],
            artifacts=[TableArtifactSpec(id="period_q3", label="period_q3", source_id="period_q3")],
        ),
    )
    pane.push(
        turn_payload(
            title="x",
            cards=[],
            panel=cast(
                PanePanel,
                {
                    "controls": [
                        {
                            "kind": "choice",
                            "id": "period",
                            "label": "Period",
                            "choices": [{"id": "q2", "label": "Q2"}, {"id": "q3", "label": "Q3"}],
                        }
                    ],
                    "default_selection": {"period": "q2"},
                },
            ),
        ),
        turn_output=TurnOutput(result.output, cast(OutputStore, FakeOutputStore())),
    )

    cards = await pane.resolve_turn(0, {"period": "q3"})

    assert cards == [
        {"id": cards[0]["id"], "artifact_id": "period_q3", "label": "period_q3", "views": ["data", "query"]}
    ]
    assert (tmp_path / f"{cards[0]['id']}.data.json").exists()


async def test_output_pane_http_resolve_runs_on_app_loop(tmp_path: Path) -> None:
    app_loop = asyncio.get_running_loop()

    class LoopCheckingOutputStore:
        async def get_payload(self, result_id: str) -> ResultPayload:
            assert asyncio.get_running_loop() is app_loop
            return ResultPayload(
                metadata=ResultMetadata(id=result_id, db_alias="workspace", query="SELECT 1"),
                df=pd.DataFrame({"period": ["q3"]}),
            )

    pane = OutputPane(tmp_path, port=_unused_loopback_port())
    pane.start()
    try:
        result = ChatResult(
            text="x",
            output=OutputSpec(
                sources=[FixedResultSource(id="S1", result_id="R1")],
                artifacts=[TableArtifactSpec(id="S1", label="period_q3", source_id="S1")],
            ),
        )
        pane.push(
            turn_payload(title="x", cards=[]),
            turn_output=TurnOutput(result.output, cast(OutputStore, LoopCheckingOutputStore())),
        )
        assert pane.url is not None
        request = urllib.request.Request(
            f"{pane.url}resolve",
            data=json.dumps({"turn_id": 0, "selection": {}}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        def post_resolve() -> dict[str, Any]:
            with urllib.request.urlopen(request, timeout=3) as response:
                return cast(dict[str, Any], json.load(response))

        payload = await asyncio.to_thread(post_resolve)
        assert payload["selection"] == {}
        assert payload["cards"] == [
            {"id": payload["cards"][0]["id"], "artifact_id": "S1", "label": "period_q3", "views": ["data", "query"]}
        ]
    finally:
        pane.stop()


def test_query_payload_contains_language_and_highlighted_html() -> None:
    payload = build_query_data('print("Hello, world!")', lexer="python")

    query = payload["query"]
    assert isinstance(query, dict)
    assert query["code"] == 'print("Hello, world!")'
    assert query["lexer"] == "python"
    assert query["language"] == "Python"
    assert "print" in str(query["html"])


def test_query_payload_normalizes_sql_dialects_and_reports_fallback_lexer() -> None:
    snowflake = build_query_data("select 1", lexer="snowflake")["query"]
    unknown = build_query_data("select 1", lexer="not-a-real-lexer")["query"]
    cypher = build_query_data("MATCH (n) RETURN n", lexer="cypher")["query"]

    assert snowflake["lexer"] == "sql"
    assert snowflake["language"] == "SQL"
    assert unknown["lexer"] == "sql"
    assert unknown["language"] == "SQL"
    assert cypher["lexer"] == "cypher"


def test_result_card_writes_structured_data_instead_of_html(tmp_path: Path) -> None:
    df = pd.DataFrame({"cat": ["a", "b"], "n": [3, 5]})
    spec = {"mark": "bar", "encoding": {"x": {"field": "cat"}, "y": {"field": "n"}}}
    card = render_result_data(
        ResultCardInput(df=df, label="x", chart_spec=spec),
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


def test_output_pane_serves_card_data_only_under_token(tmp_path: Path) -> None:
    df = pd.DataFrame({"cat": ["a"], "n": [3]})
    card = render_result_data(
        ResultCardInput(df=df, label="x"),
        tmp_path,
    )
    assert card is not None

    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        with urllib.request.urlopen(f"{pane.url}{card['id']}.data.json", timeout=2) as resp:
            payload = json.loads(resp.read())
        assert payload["dataset"]["rows"] == [{"c0": "a", "c1": 3}]

        try:
            urllib.request.urlopen(f"{_origin_url(pane.url)}{card['id']}.data.json", timeout=2)
            rejected = False
        except urllib.error.HTTPError as exc:
            rejected = exc.code == 404
        assert rejected
    finally:
        pane.stop()


def test_pane_serves_bundled_assets_with_expected_cache_policy(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.start()
    try:
        assert pane.url is not None
        with urllib.request.urlopen(pane.url, timeout=2) as response:
            assert response.headers["Cache-Control"] == "no-store"
            assert response.headers["Referrer-Policy"] == "no-referrer"

        origin = _origin_url(pane.url)
        cases = [
            ("assets/ui/pane.js", "no-cache", "text/javascript"),
            ("assets/vendor/maplibre/shortbread-light.json", "no-cache", "application/json"),
            ("assets/vendor/maplibre/maplibre-gl.js", "max-age=31536000, immutable", "text/javascript"),
            ("assets/vendor/maplibre/osm-bright-sprite.png", "max-age=31536000, immutable", "image/png"),
            ("assets/vendor/katex/fonts/KaTeX_Main-Regular.woff2", "max-age=31536000, immutable", "font/woff2"),
        ]
        for relative, cache_control, content_type in cases:
            with urllib.request.urlopen(f"{origin}{relative}", timeout=2) as response:
                assert response.headers["Cache-Control"] == cache_control
                assert response.headers["Content-Type"].startswith(content_type)
                assert response.read()

        for relative in ("assets/does-not-exist.js", "assets/ui/pane-render.js"):
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(f"{origin}{relative}", timeout=2)
            assert error.value.code == 404
    finally:
        pane.stop()
