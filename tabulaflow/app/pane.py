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

_PANE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>tabulaflow · results</title>
<style>
  html, body { margin: 0; background: #0f1117; }
  #stack { padding: 12px; }
  .card {
    display: block; width: 100%; height: 80vh; border: 1px solid #21262d;
    border-radius: 8px; margin: 0 0 12px; background: #131720;
  }
  #empty { color: #6a737d; font: 14px ui-monospace, monospace; padding: 24px; }
</style>
</head>
<body>
<div id="empty">waiting for results…</div>
<div id="stack"></div>
<script>
  var shown = 0;
  function poll() {
    fetch('/__index__').then(function (r) { return r.json(); }).then(function (names) {
      if (names.length > 0) {
        var e = document.getElementById('empty');
        if (e) { e.remove(); }
      }
      var stack = document.getElementById('stack');
      for (var i = shown; i < names.length; i++) {
        var f = document.createElement('iframe');
        f.className = 'card';
        f.src = '/' + names[i];
        stack.appendChild(f);
        f.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      shown = names.length;
    }).catch(function () {});
  }
  setInterval(poll, 1000);
  poll();
</script>
</body>
</html>
"""


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
        self._results: list[str] = []
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

    def push(self, html_path: Path) -> None:
        """Record a result file (already written under the dumps dir) for the pane."""
        with self._lock:
            self._results.append(html_path.name)

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
