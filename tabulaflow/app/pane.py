"""Embedded HTTP server that mirrors the agent's cited results in a live browser pane.

Phase 1 (MVP): a stdlib ``http.server`` running in a daemon thread serves the
self-contained result HTML files written to the session dumps dir, plus a single
pane page that polls an index and appends an ``<iframe>`` per new result. The
server binds loopback only and adds no third-party dependencies.

The pane is an *additive, output-only* surface: the TUI remains the primary
interface, and every failure here is swallowed so it can never block a chat turn.
"""

from __future__ import annotations

import functools
import http.server
import json
import threading
from collections.abc import Callable
from pathlib import Path

from tabulaflow.app.theme import GITHUB_SLUG, GITHUB_URL

_GITHUB_SVG = (
    '<svg viewBox="0 0 16 16" aria-hidden="true">'
    '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38'
    " 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53"
    " .63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95"
    " 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68"
    " 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15"
    " 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2"
    ' 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>'
)

_BANNER = (
    '<header id="banner"><div id="banner-inner">'
    '<span id="logo">tabulaflow</span>'
    f'<a id="repo" href="{GITHUB_URL}" target="_blank" rel="noopener">{_GITHUB_SVG}{GITHUB_SLUG}</a>'
    "</div></header>"
)

_PANE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>tabulaflow · results</title>
<style>
  html, body { height: 100%; }
  body { margin: 0; background: #0f1117; color: #e4e4e7; display: flex; flex-direction: column;
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  #banner { border-bottom: 1px solid #21262d; background: #0f1117; flex: 0 0 auto; }
  #banner-inner { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
  #logo { color: #3eb489; font: 700 16px ui-monospace, "SF Mono", Menlo, monospace;
          letter-spacing: 0.05em; user-select: none; }
  #repo { display: inline-flex; align-items: center; gap: 6px; color: #9aa4b2;
          text-decoration: none; font-size: 13px; padding: 4px 10px; border-radius: 4px; }
  #repo:hover { background: #1f2532; color: #e4e4e7; }
  #repo svg { width: 16px; height: 16px; fill: currentColor; }
  #main { flex: 1 1 auto; display: flex; min-height: 0; }
  #turns { flex: 0 0 230px; border-right: 1px solid #21262d; overflow-y: auto; padding: 8px 0; }
  .turnitem { padding: 9px 16px; color: #6a737d; cursor: pointer; border-left: 2px solid transparent;
              font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .turnitem:hover { color: #e4e4e7; }
  .turnitem.active { color: #3eb489; border-left-color: #3eb489; background: #1a1f2a; }
  #content { flex: 1 1 auto; overflow-y: auto; min-width: 0; display: flex; }
  #content-inner { width: min(1000px, 100%); margin: 0 auto; padding: 16px; box-sizing: border-box; }
  #empty { color: #6a737d; font: 14px ui-monospace, monospace; padding: 28px; }
  .turnview { display: flex; flex-direction: column; gap: 36px; }
  .transcript { display: flex; flex-direction: column; gap: 32px; padding: 2px 4px 0; }
  .message { display: flex; min-width: 0; }
  .message-label { display: none; }
  .message-body { font-size: 15px; line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }
  .message.user { justify-content: flex-end; }
  .message.user .message-body { max-width: min(720px, 78%); padding: 10px 14px; color: #e4e4e7;
                                background: #1f2532; border-radius: 16px 16px 4px 16px;
                                box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03); }
  .message.assistant { justify-content: stretch; }
  .message.assistant .message-body { width: 100%; color: #e4e4e7; }
  @media (max-width: 640px) {
    .message.user .message-body { max-width: 92%; }
  }
  .rectabs { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px;
             margin-right: auto; min-height: 36px; }
  .rectab { background: transparent; border: 0; border-radius: 2px; color: #9aa4b2; cursor: pointer;
            padding: 5px 10px; max-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            font: 14px/1.25 ui-monospace, monospace; }
  .rectab:hover { color: #e4e4e7; background: #1f2532; }
  .rectab.active { color: #06120e; background: #3eb489; font-weight: 700; }
  .panesbox { position: relative; }
  .recordpane { width: 100%; }
  .recordpane.hidden { position: absolute; top: 0; left: 0; visibility: hidden; pointer-events: none; }
  .cardbar { display: flex; align-items: center; gap: 8px; min-height: 40px; padding: 6px 4px 14px;
             font: 13px ui-monospace, monospace; }
  .cardlabel { display: inline-flex; max-width: 180px; margin-right: auto; padding: 5px 10px;
               overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
               color: #06120e; background: #3eb489; border-radius: 2px;
               font: 700 14px/1.25 ui-monospace, monospace; }
  .seg { position: relative; display: inline-flex; padding: 3px; border-radius: 999px;
         box-shadow: inset 0 0 0 1px #21262d; }
  .seg-opt { position: relative; z-index: 1; background: transparent; border: 0; cursor: pointer;
             color: #6a737d; padding: 7px 16px; border-radius: 999px; text-transform: capitalize;
             font: 13px/1.2 ui-monospace, monospace; transition: color 0.18s ease; }
  .seg-opt:hover { color: #e4e4e7; }
  .seg-opt.active { color: #3eb489; }
  .seg-thumb { position: absolute; top: 3px; bottom: 3px; left: 0; width: 0; border-radius: 999px;
               background: #262c36; }
  .seg-thumb.ready { transition: transform 0.22s ease, width 0.22s ease; }
  .cardframe { display: block; width: 100%; height: 320px; background: #1a212c;
               border: 0; border-radius: 10px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35); }
</style>
</head>
<body>
__BANNER__
<div id="main">
<aside id="turns"></aside>
<div id="content"><div id="content-inner"><div id="empty">waiting for results…</div></div></div>
</div>
<script>
  // Cards are served same-origin, so the parent tracks each iframe's content
  // height (ResizeObserver) and resizes to fit as Tabulator/Vega render. Measure
  // <body> (whose scrollHeight hugs the content) rather than documentElement
  // (floored at the iframe viewport, so it can't shrink back for short content).
  function autosize(frame) {
    var ro = null;
    frame.addEventListener('load', function () {
      try {
        var doc = frame.contentWindow.document;
        var fit = function () { frame.style.height = doc.body.scrollHeight + 'px'; };
        fit();
        if (ro) { ro.disconnect(); }
        if (window.ResizeObserver) { ro = new ResizeObserver(fit); ro.observe(doc.body); }
      } catch (e) { /* cross-origin / detached — keep the CSS height */ }
    });
  }
  function el(tag, cls) { var e = document.createElement(tag); if (cls) { e.className = cls; } return e; }
  function hasText(value) { return typeof value === 'string' && value.trim().length > 0; }
  function moveThumb(thumb, opt) {
    thumb.style.width = opt.offsetWidth + 'px';
    thumb.style.transform = 'translateX(' + opt.offsetLeft + 'px)';
  }
  function buildMessage(role, text) {
    var msg = el('div', 'message ' + role);
    var label = el('div', 'message-label');
    var body = el('div', 'message-body');
    label.textContent = role === 'user' ? 'user' : 'tabulaflow';
    body.textContent = text;
    msg.appendChild(label);
    msg.appendChild(body);
    return msg;
  }
  function buildTranscript(turn) {
    var wrap = el('section', 'transcript');
    if (hasText(turn.user)) { wrap.appendChild(buildMessage('user', turn.user)); }
    if (hasText(turn.assistant)) { wrap.appendChild(buildMessage('assistant', turn.assistant)); }
    return wrap.children.length ? wrap : null;
  }
  // Build one record's pane: a Chart|Data|Query tab strip + iframe. The chart
  // loads up front; Data/Query load lazily on tab click.
  function buildRecord(record, recOpts) {
    var pane = el('div', 'recordpane');
    var bar = el('div', 'cardbar');
    if (recOpts) {
      var tabs = el('div', 'rectabs');
      recOpts.records.forEach(function (rt, i) {
        var t = el('button', 'rectab');
        t.textContent = rt.label || ('result ' + (i + 1));
        t.title = t.textContent;
        if (i === recOpts.activeIndex) { t.classList.add('active'); }
        t.onclick = function () { recOpts.onSelect(i); };
        tabs.appendChild(t);
      });
      bar.appendChild(tabs);
    } else if (record.label) {
      var lbl = el('span', 'cardlabel');
      lbl.textContent = record.label;
      bar.appendChild(lbl);
    }
    var frame = el('iframe', 'cardframe');
    frame.scrolling = 'no';
    autosize(frame);
    var seg = el('div', 'seg');
    var thumb = el('span', 'seg-thumb');
    seg.appendChild(thumb);
    var opts = [];
    (record.views || []).forEach(function (v) {
      var o = el('button', 'seg-opt');
      o.textContent = v.kind;
      o.onclick = function () {
        frame.src = '/' + v.file;
        opts.forEach(function (x) { x.classList.remove('active'); });
        o.classList.add('active');
        moveThumb(thumb, o);
      };
      opts.push(o);
      seg.appendChild(o);
    });
    if (opts.length) { bar.appendChild(seg); }
    pane.appendChild(bar);
    pane.appendChild(frame);
    if (opts.length) {
      frame.src = '/' + record.views[0].file;
      opts[0].classList.add('active');
      requestAnimationFrame(function () {
        moveThumb(thumb, opts[0]);
        requestAnimationFrame(function () { thumb.classList.add('ready'); });
      });
    }
    return pane;
  }
  // Render the active turn: the record's pane(s) directly (no card frame). A
  // multi-result turn carries record tabs in each pane's header (left of the view
  // segmented); panes are pre-built and toggled by visibility (flicker-free switch).
  function renderTurn(turn) {
    var view = el('div', 'turnview');
    var transcript = buildTranscript(turn);
    if (transcript) { view.appendChild(transcript); }
    var records = turn.records || [];
    if (!records.length) {
      return view;
    }
    if (records.length <= 1) {
      view.appendChild(buildRecord(records[0], null));
      return view;
    }
    var box = el('div', 'panesbox');
    var panes = [];
    function onSelect(i) { panes.forEach(function (p, j) { p.classList.toggle('hidden', j !== i); }); }
    records.forEach(function (rec, i) {
      var pane = buildRecord(rec, { records: records, activeIndex: i, onSelect: onSelect });
      if (i !== 0) { pane.classList.add('hidden'); }
      box.appendChild(pane);
      panes.push(pane);
    });
    view.appendChild(box);
    return view;
  }
  // Turn navigator: the sidebar lists every turn; only the selected turn is
  // rendered (iframes never accumulate). New turns are appended and auto-selected.
  var turns = [];
  function selectTurn(i) {
    if (i < 0 || i >= turns.length) { return; }
    var items = document.querySelectorAll('#turns .turnitem');
    for (var k = 0; k < items.length; k++) { items[k].classList.toggle('active', k === i); }
    var inner = document.getElementById('content-inner');
    inner.innerHTML = '';
    inner.appendChild(renderTurn(turns[i]));
  }
  function poll() {
    fetch('/__index__').then(function (r) { return r.json(); }).then(function (server) {
      if (server.length <= turns.length) { return; }
      var sidebar = document.getElementById('turns');
      for (var i = turns.length; i < server.length; i++) {
        turns.push(server[i]);
        var it = el('div', 'turnitem');
        it.textContent = server[i].title || ('Turn ' + (i + 1));
        it.title = it.textContent;
        (function (idx) { it.onclick = function () { selectTurn(idx); }; })(i);
        sidebar.appendChild(it);
      }
      selectTurn(turns.length - 1);
    }).catch(function () {});
  }
  setInterval(poll, 1000);
  poll();
</script>
</body>
</html>
""".replace("__BANNER__", _BANNER)


class _PaneServer(http.server.ThreadingHTTPServer):
    """``ThreadingHTTPServer`` carrying a back-reference to its ``OutputPane``."""

    def __init__(
        self,
        server_address: tuple[str, int],
        handler: Callable[..., http.server.BaseHTTPRequestHandler],
        pane: OutputPane,
    ) -> None:
        super().__init__(server_address, handler)
        self.pane = pane


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Serves the pane page and result index; falls back to static dump files."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API name)
        if self.path in ("/", "/index.html"):
            self._send(_PANE_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/__index__":
            assert isinstance(self.server, _PaneServer)
            with self.server.pane._lock:
                payload = json.dumps(self.server.pane._results)
            self._send(payload.encode("utf-8"), "application/json")
            return
        super().do_GET()

    def _send(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Silence request logging — stray stderr would corrupt the TUI."""


class OutputPane:
    """A loopback HTTP server plus browser tab showing cited results as they arrive."""

    def __init__(self, dumps_dir: Path) -> None:
        self._dumps_dir = dumps_dir
        self._results: list[dict[str, object]] = []
        self._lock = threading.Lock()
        self._server: _PaneServer | None = None
        self._port: int | None = None
        self._browser_opened = False

    def start(self) -> None:
        """Bind a loopback server on a free port and serve it in a daemon thread."""
        handler = functools.partial(_Handler, directory=str(self._dumps_dir))
        self._server = _PaneServer(("127.0.0.1", 0), handler, self)
        self._port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    @property
    def url(self) -> str | None:
        return f"http://127.0.0.1:{self._port}/" if self._port is not None else None

    def push(self, turn: dict[str, object]) -> None:
        """Record a turn ({"records": [{"label", "views": [...]}, ...]}) for the pane."""
        with self._lock:
            self._results.append(turn)

    def open_browser(self, *, force: bool = False) -> None:
        """Open the pane in the system browser (once unless ``force``; no-op if headless)."""
        if self.url is None or (self._browser_opened and not force):
            return
        self._browser_opened = True
        try:
            import webbrowser_open

            webbrowser_open.open(self.url)
        except Exception:
            pass

    def reopen(self) -> None:
        """Force (re)open the pane in the browser — for explicit user actions."""
        self.open_browser(force=True)

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None
