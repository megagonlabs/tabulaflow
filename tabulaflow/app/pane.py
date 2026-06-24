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
  html, body { margin: 0; background: #0f1117;
               font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  #banner { border-bottom: 1px solid #21262d; background: #0f1117; position: sticky; top: 0; z-index: 50; }
  #banner-inner { display: flex; align-items: center; justify-content: space-between;
                  max-width: 1100px; margin: 0 auto; padding: 12px 14px; }
  #logo { color: #3eb489; font: 700 16px ui-monospace, "SF Mono", Menlo, monospace;
          letter-spacing: 0.05em; user-select: none; }
  #repo { display: inline-flex; align-items: center; gap: 6px; color: #9aa4b2;
          text-decoration: none; font-size: 13px; padding: 4px 10px; border-radius: 4px; }
  #repo:hover { background: #1f2532; color: #e4e4e7; }
  #repo svg { width: 16px; height: 16px; fill: currentColor; }
  #stack { padding: 12px; max-width: 1100px; margin: 0 auto; }
  .card { border: 1px solid #21262d; border-radius: 8px; margin: 0 0 14px;
          background: #131720; overflow: hidden; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3); }
  .railcard { display: flex; align-items: stretch; }
  .rail { flex: 0 0 170px; border-right: 1px solid #21262d; padding: 6px 0; }
  .railitem { padding: 8px 14px; color: #6a737d; cursor: pointer; border-left: 2px solid transparent;
              font: 12px ui-monospace, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .railitem:hover { color: #e4e4e7; }
  .railitem.active { color: #3eb489; border-left-color: #3eb489; background: #1a1f2a; }
  .railcontent { flex: 1 1 auto; min-width: 0; position: relative; }
  .recordpane { width: 100%; }
  .recordpane.hidden { position: absolute; top: 0; left: 0; visibility: hidden; pointer-events: none; }
  .cardbar { display: flex; align-items: center; justify-content: flex-end; gap: 8px; padding: 8px 10px;
             font: 12px ui-monospace, monospace; }
  .cardlabel { color: #e4e4e7; margin-right: auto; }
  .seg { position: relative; display: inline-flex; padding: 3px; border-radius: 999px;
         box-shadow: inset 0 0 0 1px #21262d; }
  .seg-opt { position: relative; z-index: 1; background: transparent; border: 0; cursor: pointer;
             color: #6a737d; padding: 4px 14px; border-radius: 999px; text-transform: capitalize;
             font: 12px ui-monospace, monospace; transition: color 0.18s ease; }
  .seg-opt:hover { color: #e4e4e7; }
  .seg-opt.active { color: #3eb489; }
  .seg-thumb { position: absolute; top: 3px; bottom: 3px; left: 0; width: 0; border-radius: 999px;
               background: #262c36; }
  .seg-thumb.ready { transition: transform 0.22s ease, width 0.22s ease; }
  .cardframe { display: block; width: 100%; height: 320px; border: 0; background: #131720; }
  #empty { color: #6a737d; font: 14px ui-monospace, monospace; padding: 24px; }
</style>
</head>
<body>
__BANNER__
<div id="empty">waiting for results…</div>
<div id="stack"></div>
<script>
  // Cards are served same-origin, so the parent tracks each iframe's content
  // height (ResizeObserver) and resizes the card to fit as Tabulator/Vega render.
  function autosize(frame) {
    var ro = null;
    frame.addEventListener('load', function () {
      try {
        var doc = frame.contentWindow.document;
        var fit = function () { frame.style.height = doc.documentElement.scrollHeight + 'px'; };
        fit();
        if (ro) { ro.disconnect(); }
        if (window.ResizeObserver) { ro = new ResizeObserver(fit); ro.observe(doc.documentElement); }
      } catch (e) { /* cross-origin / detached — keep the CSS height */ }
    });
  }
  function el(tag, cls) { var e = document.createElement(tag); if (cls) { e.className = cls; } return e; }
  function moveThumb(thumb, opt) {
    thumb.style.width = opt.offsetWidth + 'px';
    thumb.style.transform = 'translateX(' + opt.offsetLeft + 'px)';
  }
  // Build one record's pane: a Chart|Data|Query tab strip + iframe. The chart
  // loads up front; Data/Query load lazily on tab click.
  function buildRecord(record, labelText) {
    var pane = el('div', 'recordpane');
    var bar = el('div', 'cardbar');
    if (labelText) { var lbl = el('span', 'cardlabel'); lbl.textContent = labelText; bar.appendChild(lbl); }
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
  // A turn is one card with a left record rail (one item per cited result); all
  // record panes are pre-built and toggled by visibility, so switching is a CSS
  // toggle (no iframe reload, no flicker), not a re-render.
  function makeTurn(turn) {
    var card = el('div', 'card');
    var records = turn.records || [];
    if (records.length === 0) {
      card.appendChild(buildRecord({ views: [] }, null));
      return card;
    }
    card.classList.add('railcard');
    var rail = el('div', 'rail');
    var content = el('div', 'railcontent');
    var items = [];
    var panes = [];
    records.forEach(function (rec, i) {
      var pane = buildRecord(rec, null);
      if (i !== 0) { pane.classList.add('hidden'); }
      content.appendChild(pane);
      panes.push(pane);
      var it = el('div', 'railitem');
      it.textContent = rec.label || ('result ' + (i + 1));
      it.title = it.textContent;
      it.onclick = function () {
        items.forEach(function (x) { x.classList.remove('active'); });
        it.classList.add('active');
        panes.forEach(function (p, j) { p.classList.toggle('hidden', j !== i); });
      };
      items.push(it);
      rail.appendChild(it);
    });
    items[0].classList.add('active');
    card.appendChild(rail);
    card.appendChild(content);
    return card;
  }
  var shown = 0;
  function poll() {
    fetch('/__index__').then(function (r) { return r.json(); }).then(function (turns) {
      if (turns.length > 0) {
        var e = document.getElementById('empty');
        if (e) { e.remove(); }
      }
      var stack = document.getElementById('stack');
      for (var i = shown; i < turns.length; i++) {
        var node = makeTurn(turns[i]);
        stack.appendChild(node);
        node.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      shown = turns.length;
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
