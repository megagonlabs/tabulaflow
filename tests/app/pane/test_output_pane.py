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

from tabulaflow.app.config import LLM_OFF, ResolvedLLMConfig
from tabulaflow.app.pane.cards import (
    ResultCardInput,
    render_result_data,
)
from tabulaflow.app.pane.contract import PaneCard, PanePanel, PaneTurn, turn_payload
from tabulaflow.app.pane.server import OutputPane, OutputPanePortError
from tabulaflow.app.runtime_paths import RuntimePaths
from tabulaflow.app.tui import TabulaflowApp
from tabulaflow.app.turn import TurnOutput
from tabulaflow.agents.chat import ChatResult
from tabulaflow.output.specs import (
    ChoiceOption,
    ChoiceParameter,
    FixedArtifactSource,
    OutputSpec,
    TableArtifactSpec,
)
from tabulaflow.output.store import OutputStore, ResultMetadata, MaterializedResult


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


def _renderer_module(tmp_path: Path, *files_to_copy: str) -> tuple[str, str]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute browser renderers")

    source = files("tabulaflow.app.pane.assets").joinpath("ui", "render")
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    for name in files_to_copy:
        module_dir.joinpath(name).write_text(source.joinpath(name).read_text(encoding="utf-8"), encoding="utf-8")
    module_dir.joinpath("package.json").write_text('{"type":"module"}', encoding="utf-8")
    return node, str(module_dir / files_to_copy[-1])


def _run_node(node: str, script: str) -> Any:
    result = subprocess.run(
        [node, "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_color_domain_registry_preserves_observed_order_and_explicit_domains(tmp_path: Path) -> None:
    node, module_path = _renderer_module(tmp_path, "shared.js", "color-domains.js")
    script = f"""
import {{ pathToFileURL }} from 'node:url';
const moduleUrl = pathToFileURL({json.dumps(module_path)}).href;
const {{ stableColorDomain }} = await import(moduleUrl);

console.log(JSON.stringify({{
  first: stableColorDomain('artifact:color', null, ['A', 'B']),
  second: stableColorDomain('artifact:color', null, ['B', 'C']),
  explicit: stableColorDomain('artifact:explicit', ['C', 'A'], ['A', 'B'])
}}));
"""

    result = _run_node(node, script)

    assert result == {
        "first": ["A", "B"],
        "second": ["A", "B", "C"],
        "explicit": ["C", "A"],
    }


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


def test_output_pane_completes_pending_turn_in_place(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)

    turn_id = pane.begin_turn(title="analyze", user="Analyze the data.")
    pane.complete_turn(
        turn_id,
        turn_payload(
            title="analyze",
            user="Analyze the data.",
            assistant="Done.",
            cards=[],
        ),
    )

    events = pane._wait_for_events(-1, timeout=0)  # noqa: SLF001
    assert events == [
        (0, "turn", {"id": 0, "status": "pending", "title": "analyze", "user": "Analyze the data."}),
        (
            1,
            "turn",
            {"id": 0, "title": "analyze", "user": "Analyze the data.", "assistant": "Done.", "cards": []},
        ),
    ]


def test_output_pane_discards_pending_turn(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)

    turn_id = pane.begin_turn(title="analyze", user="Analyze the data.")
    pane.discard_turn(turn_id)

    assert pane._wait_for_events(0, timeout=0) == [(1, "turn-remove", {"id": turn_id})]  # noqa: SLF001


def test_output_pane_clear_resets_current_history(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    stale_turn_id = pane.begin_turn(title="analyze", user="Analyze the data.")
    pane.push(turn_payload(title="result", cards=[]))

    pane.clear()

    assert pane._wait_for_events(-1, timeout=0) == [(2, "clear", {})]  # noqa: SLF001
    with pytest.raises(KeyError):
        pane.complete_turn(stale_turn_id, turn_payload(title="stale", cards=[]))

    new_turn_id = pane.begin_turn(title="new", user="Start fresh.")
    assert new_turn_id == 2
    assert pane._wait_for_events(2, timeout=0) == [
        (3, "turn", {"id": 2, "status": "pending", "title": "new", "user": "Start fresh."})
    ]


def test_output_pane_replaces_pending_turn_in_browser(tmp_path: Path) -> None:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

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
                page = browser.new_page(viewport={"width": 1_280, "height": 720})
                page.goto(pane.url, wait_until="domcontentloaded")
                page.evaluate("document.hasFocus = () => false")
                turn_id = pane.begin_turn(title="analyze", user="Analyze the data.")

                page.wait_for_selector(".pending-turn")
                assert page.locator(".turnitem").count() == 1
                assert page.locator(".turnmeta").text_content() == "working"
                assert page.title() == "tabulaflow"

                pane.complete_turn(
                    turn_id,
                    turn_payload(
                        title="analyze",
                        user="Analyze the data.",
                        assistant="Done.",
                        cards=[],
                    ),
                )

                page.wait_for_selector(".message.assistant")
                assert page.locator(".turnitem").count() == 1
                assert page.locator(".pending-turn").count() == 0
                assert page.locator(".message.assistant .message-body").inner_text() == "Done."
                assert page.title() == "◆ tabulaflow"

                pane.clear()

                page.wait_for_selector("#empty")
                assert page.locator(".turnitem").count() == 0
                assert page.locator(".turns-empty").inner_text() == "No output yet"
                assert page.title() == "tabulaflow"
            finally:
                browser.close()
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


def test_manual_table_send_includes_data_view_meta(tmp_path: Path) -> None:
    pushed: list[PaneTurn] = []

    class FakePane:
        url = "http://127.0.0.1:61111/"

        def push(self, turn: PaneTurn) -> None:
            pushed.append(turn)

    df = pd.DataFrame({"sample_id": ["ex-0001", "ex-0002"], "answer": ["A", "B"]})
    runtime_paths = _runtime_paths(tmp_path)
    app = TabulaflowApp(
        llm_config=ResolvedLLMConfig(LLM_OFF, None),
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


def test_large_manual_table_scrolls_inside_viewport(tmp_path: Path) -> None:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    card = render_result_data(
        ResultCardInput(df=pd.DataFrame({"row_id": range(1_000), "value": range(1_000)}), label="manual"),
        tmp_path,
    )
    assert card is not None
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
                page = browser.new_page(viewport={"width": 1_280, "height": 720})
                page.goto(pane.url, wait_until="domcontentloaded")
                pane.push(turn_payload(title="manual", source="manual", cards=[card]))
                page.wait_for_selector(".manual-preview .tabulator-tableholder")
                page.wait_for_function(
                    "document.querySelector('.manual-preview .tabulator-tableholder').scrollHeight > "
                    "document.querySelector('.manual-preview .tabulator-tableholder').clientHeight"
                )
                dimensions = page.evaluate(
                    """() => {
                      const content = document.querySelector('#content');
                      const holder = document.querySelector('.manual-preview .tabulator-tableholder');
                      return {
                        contentClientHeight: content.clientHeight,
                        contentScrollHeight: content.scrollHeight,
                        holderClientHeight: holder.clientHeight,
                        holderScrollHeight: holder.scrollHeight,
                      };
                    }"""
                )
                assert dimensions["contentScrollHeight"] == dimensions["contentClientHeight"]
                assert dimensions["holderScrollHeight"] > dimensions["holderClientHeight"]
            finally:
                browser.close()
    finally:
        pane.stop()


def test_pane_markdown_renderer_formats_safe_markdown(tmp_path: Path) -> None:
    assets = files("tabulaflow.app.pane.assets")
    vendor_path = str(assets.joinpath("vendor").joinpath("markdown-it").joinpath("markdown-it.min.js"))
    node, renderer_path = _renderer_module(tmp_path, "shared.js", "code.js", "markdown.js")
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
    rendered = _run_node(node, script)

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
    assets = files("tabulaflow.app.pane.assets")
    markdown_it_path = str(assets.joinpath("vendor").joinpath("markdown-it").joinpath("markdown-it.min.js"))
    katex_path = str(assets.joinpath("vendor").joinpath("katex").joinpath("katex.min.js"))
    texmath_path = str(assets.joinpath("vendor").joinpath("markdown-it-texmath").joinpath("texmath.js"))
    node, renderer_path = _renderer_module(tmp_path, "shared.js", "code.js", "markdown.js")
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
    rendered = _run_node(node, script)

    assert rendered["classes"] == ["md"]
    assert '<span class="katex">' in rendered["html"]
    assert '<eq><span class="katex">' in rendered["html"]
    assert '<eqn><span class="katex-display">' in rendered["html"]
    assert "Price stays literal: $100 and $200." in rendered["html"]


def test_pane_code_copy_button_shows_copied_feedback(tmp_path: Path) -> None:
    node, renderer_path = _renderer_module(tmp_path, "shared.js", "code.js")
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
    rendered = _run_node(node, script)

    assert 'data-copy-code aria-label="Copy query" title="Copy query"' in rendered["html"]
    assert rendered["copied"] == {"classes": ["copied"], "label": "Copied query", "title": "Copied", "timerMs": 1200}
    assert rendered["reset"] == {"classes": [], "label": "Copy query", "title": "Copy query"}


def test_table_copy_serializes_complete_values_as_tsv(tmp_path: Path) -> None:
    node, renderer_path = _renderer_module(tmp_path, "shared.js", "table.js")
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
  {{ title: 'Media without size', field: 'mediaWithoutSize' }},
];
const rows = [
  {{ name: 'Alice', notes: 'one\\ttwo', meta: {{ a: 1 }},
     media: {{ kind: 'media', mime: 'image/png', src: 'data:image/png;base64,AAAA', size: 123 }},
     mediaWithoutSize: {{ kind: 'media', mime: 'audio/mpeg', src: './private/audio.mp3' }} }},
  {{ name: 'Bob', notes: 'line\\n"quoted"', meta: null,
     media: {{ kind: 'media', mime: 'application/pdf', src: './private/file.pdf', size: 456 }},
     mediaWithoutSize: {{ kind: 'media-list', items: [
       {{ kind: 'media', mime: 'image/png', src: './private/one.png', size: 12 }},
       {{ kind: 'media', mime: 'image/jpeg', src: './private/two.jpg', size: 34 }},
       {{ kind: 'media', mime: 'application/pdf', src: './private/file.pdf', size: 456 }},
       {{ kind: 'media', mime: 'audio/mpeg', src: './private/audio.mp3', size: 78 }}
     ] }} }},
];
process.stdout.write(JSON.stringify(tableToTsv(columns, rows)));
"""
    assert _run_node(node, script) == (
        "Name\tNotes\tMeta\tMedia\tMedia without size\n"
        'Alice\t"one\ttwo"\t"{""a"":1}"\t[Media: image/png, 123 bytes]\t[Media: audio/mpeg]\n'
        'Bob\t"line\n""quoted"""\t\t[Media: application/pdf, 456 bytes]\t'
        "[4 media items: 2 images, 1 PDF, 1 audio]"
    )


def test_table_image_cells_reserve_stable_preview_space(tmp_path: Path) -> None:
    node, renderer_path = _renderer_module(tmp_path, "shared.js", "table.js")
    script = f"""
import {{ pathToFileURL }} from 'node:url';
globalThis.window = {{ Tabulator: {{}} }};
const moduleUrl = pathToFileURL({json.dumps(renderer_path)}).href;
const {{ renderMediaCell }} = await import(moduleUrl);
const image = {{ kind: 'media', mime: 'image/png', src: './image.png', size: 123 }};
process.stdout.write(JSON.stringify({{
  scalar: renderMediaCell(image),
  singleton: renderMediaCell({{ kind: 'media-list', items: [image] }}),
  collection: renderMediaCell({{ kind: 'media-list', items: [image, image] }}),
}}));
"""

    rendered = _run_node(node, script)

    assert rendered["scalar"] == '<div class="tf-media-preview"><img src="./image.png"></div>'
    assert rendered["singleton"] == rendered["scalar"]
    assert 'class="tf-media-list"' in rendered["collection"]
    assert 'class="tf-media-preview"' not in rendered["collection"]


def test_lightbox_media_uses_context_specific_controls(tmp_path: Path) -> None:
    node, renderer_path = _renderer_module(tmp_path, "shared.js")
    script = f"""
import {{ pathToFileURL }} from 'node:url';
const moduleUrl = pathToFileURL({json.dumps(renderer_path)}).href;
const {{ renderMedia }} = await import(moduleUrl);
const audio = {{ kind: 'media', mime: 'audio/mpeg', src: './audio.mp3', size: 123 }};
const pdf = {{ kind: 'media', mime: 'application/pdf', src: './file.pdf', size: 2048 }};
process.stdout.write(JSON.stringify({{
  tableAudio: renderMedia(audio),
  lightboxAudio: renderMedia(audio, 'lightbox'),
  lightboxPdf: renderMedia(pdf, 'lightbox'),
}}));
"""

    rendered = _run_node(node, script)

    assert 'preload="none"' in rendered["tableAudio"]
    assert 'preload="metadata"' in rendered["lightboxAudio"]
    assert 'class="tf-lightbox-file"' in rendered["lightboxPdf"]
    assert "PDF document" in rendered["lightboxPdf"]
    assert "2.0 KB &middot; Open PDF" in rendered["lightboxPdf"]


def test_format_json_text_distinguishes_structured_values(tmp_path: Path) -> None:
    node, renderer_path = _renderer_module(tmp_path, "shared.js")
    script = f"""
import {{ pathToFileURL }} from 'node:url';
const moduleUrl = pathToFileURL({json.dumps(renderer_path)}).href;
const {{ formatJsonText }} = await import(moduleUrl);
process.stdout.write(JSON.stringify({{
  valid: formatJsonText('{{"nested":{{"value":1}}}}'),
  invalid: formatJsonText('{{not json}}'),
  plain: formatJsonText('plain text'),
}}));
"""

    rendered = _run_node(node, script)

    assert rendered == {
        "valid": '{\n  "nested": {\n    "value": 1\n  }\n}',
        "invalid": None,
        "plain": None,
    }


def test_output_pane_push_highlights_assistant_markdown_code_blocks(tmp_path: Path) -> None:
    pane = OutputPane(tmp_path)
    pane.push(
        turn_payload(
            title="code",
            cards=[],
            assistant="Before\n\n```python\nprint('hi')\n```\n\n```\nplain\n```",
        )
    )

    turn = pane._wait_for_events(-1, timeout=0)[0][2]  # noqa: SLF001
    assert isinstance(turn, dict)
    blocks = turn["assistantCodeBlocks"]
    assert blocks[0]["code"] == "print('hi')\n"
    assert [block["lexer"] for block in blocks] == ["python", "text"]
    assert blocks[0]["language"] == "Python"
    assert "print" in blocks[0]["html"]
    assert "#E0E0E0" in blocks[0]["html"]


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
        llm_config=ResolvedLLMConfig(LLM_OFF, None),
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
        async def get_result(self, result_id: str) -> MaterializedResult:
            return MaterializedResult(
                metadata=ResultMetadata(
                    id=result_id,
                    connector_alias="workspace",
                    query="SELECT 1",
                    query_language="duckdb",
                ),
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
            sources=[FixedArtifactSource(id="period_q3", result_id="Q1")],
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
        async def get_result(self, result_id: str) -> MaterializedResult:
            assert asyncio.get_running_loop() is app_loop
            return MaterializedResult(
                metadata=ResultMetadata(
                    id=result_id,
                    connector_alias="workspace",
                    query="SELECT 1",
                    query_language="duckdb",
                ),
                df=pd.DataFrame({"period": ["q3"]}),
            )

    pane = OutputPane(tmp_path, port=_unused_loopback_port())
    pane.start()
    try:
        result = ChatResult(
            text="x",
            output=OutputSpec(
                sources=[FixedArtifactSource(id="S1", result_id="R1")],
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
            assert b"/assets/fonts/figtree/Figtree-Variable.woff2" in response.read()

        origin = _origin_url(pane.url)
        cases = [
            ("assets/ui/pane.js", "no-cache", "text/javascript"),
            ("assets/vendor/maplibre/shortbread-light.json", "no-cache", "application/json"),
            ("assets/vendor/maplibre/maplibre-gl.js", "max-age=31536000, immutable", "text/javascript"),
            ("assets/vendor/maplibre/osm-bright-sprite.png", "max-age=31536000, immutable", "image/png"),
            ("assets/vendor/katex/fonts/KaTeX_Main-Regular.woff2", "max-age=31536000, immutable", "font/woff2"),
            ("assets/fonts/figtree/Figtree-Variable.woff2", "max-age=31536000, immutable", "font/woff2"),
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
