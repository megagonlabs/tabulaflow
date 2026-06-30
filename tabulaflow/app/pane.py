"""Embedded HTTP server that mirrors the agent's cited results in a live browser pane.

A stdlib ``http.server`` running in a daemon thread serves the single-page pane,
structured record-data files written to the session dumps dir, and a Server-Sent
Events stream of turn manifests. The server binds loopback only and adds no
third-party dependencies.

The pane is an *additive, output-only* surface: the TUI remains the primary
interface, and every failure here is swallowed so it can never block a chat turn.
"""

from __future__ import annotations

import functools
import http.server
import json
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from tabulaflow.app.pane_types import PaneTurn
from tabulaflow.app.theme import GITHUB_SLUG, GITHUB_URL

DEFAULT_OUTPUT_PANE_PORT_START = 61111
DEFAULT_OUTPUT_PANE_PORT_END = 61130
DEFAULT_OUTPUT_PANE_PORTS = tuple(range(DEFAULT_OUTPUT_PANE_PORT_START, DEFAULT_OUTPUT_PANE_PORT_END + 1))
DEFAULT_OUTPUT_PANE_HOST = "127.0.0.1"

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


def _pane_css_vars() -> str:
    from tabulaflow.app.page import (
        BORDER,
        CARD_BG,
        PAGE_BG,
        ROW_HOVER,
        ROW_STRIPE,
        TEXT,
        TEXT_DIM,
        TEXT_MUTED,
    )
    from tabulaflow.app.theme import ACCENT

    return (
        ":root {"
        f"--accent: {ACCENT};"
        f"--bg: {PAGE_BG};"
        f"--card: {CARD_BG};"
        f"--stripe: {ROW_STRIPE};"
        f"--hover: {ROW_HOVER};"
        f"--border: {BORDER};"
        f"--text: {TEXT};"
        f"--text-muted: {TEXT_MUTED};"
        f"--text-dim: {TEXT_DIM};"
        "--panel: #1f2532;"
        "--rail-bg: #131720;"
        "}"
    )


def _load_pane_html() -> str:
    from importlib.resources import files

    base = files("tabulaflow.app.assets.pane")
    html = base.joinpath("index.html").read_text(encoding="utf-8")
    css = base.joinpath("pane.css").read_text(encoding="utf-8")
    js = base.joinpath("pane.js").read_text(encoding="utf-8")
    return (
        html.replace("__CSS_VARS__", _pane_css_vars())
        .replace("__PANE_CSS__", css)
        .replace("__PANE_JS__", js)
        .replace("__BANNER__", _BANNER)
    )


_PANE_HTML = _load_pane_html()


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
        if self.path == "/events":
            self._serve_events()
            return
        if self.path.startswith("/assets/"):
            self._serve_asset(self.path[len("/assets/") :])
            return
        super().do_GET()

    def _send(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_events(self) -> None:
        """Stream pane turns as Server-Sent Events, replaying missed turns."""
        assert isinstance(self.server, _PaneServer)
        pane = self.server.pane
        try:
            last_id = int(self.headers.get("Last-Event-ID", "-1"))
        except ValueError:
            last_id = -1
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        while True:
            heartbeat = False
            with pane._cond:
                pending = [turn for turn in pane._results if int(turn.get("id", -1)) > last_id]
                if not pending:
                    pane._cond.wait(timeout=15)
                    pending = [turn for turn in pane._results if int(turn.get("id", -1)) > last_id]
                    heartbeat = not pending
            try:
                if heartbeat:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                for turn in pending:
                    turn_id = int(turn["id"])
                    data = json.dumps(turn, ensure_ascii=False)
                    self.wfile.write(f"id: {turn_id}\nevent: turn\ndata: {data}\n\n".encode("utf-8"))
                    last_id = turn_id
                self.wfile.flush()
            except (BrokenPipeError, ConnectionError, OSError):
                return

    def _serve_asset(self, rel: str) -> None:
        """Serve bundled browser assets with immutable caching."""
        from importlib.resources import files

        clean = rel.split("?", 1)[0]
        parts = [p for p in clean.split("/") if p]
        if not parts or ".." in parts:
            self.send_error(404)
            return
        resource = files("tabulaflow.app.assets")
        for part in parts:
            resource = resource.joinpath(part)
        try:
            data = resource.read_bytes()
        except (FileNotFoundError, OSError):
            self.send_error(404)
            return
        if clean.endswith(".js"):
            ctype = "text/javascript; charset=utf-8"
        elif clean.endswith(".css"):
            ctype = "text/css; charset=utf-8"
        else:
            ctype = "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        """Silence request logging — stray stderr would corrupt the TUI."""


class OutputPanePortError(RuntimeError):
    """Raised when the output pane cannot bind its configured loopback port(s)."""


class OutputPane:
    """A loopback HTTP server plus browser tab showing cited results as they arrive."""

    def __init__(
        self,
        dumps_dir: Path,
        *,
        host: str = DEFAULT_OUTPUT_PANE_HOST,
        port: int | None = None,
        port_range: Sequence[int] = DEFAULT_OUTPUT_PANE_PORTS,
    ) -> None:
        self._dumps_dir = dumps_dir
        self._host = host.strip()
        if not self._host:
            raise ValueError("Output pane host cannot be empty.")
        self._port_config = port
        self._port_range = tuple(port_range)
        self._results: list[PaneTurn] = []
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._next_id = 0
        self._server: _PaneServer | None = None
        self._port: int | None = None
        self._browser_opened = False

    def start(self) -> None:
        """Bind the pane server and serve it in a daemon thread.

        With no explicit port, the pane takes the first available port from the
        stable default range. An explicit port is strict and fails if occupied.
        """
        host = self._host
        handler = functools.partial(_Handler, directory=str(self._dumps_dir))
        ports = (self._port_config,) if self._port_config is not None else self._port_range
        last_error: OSError | None = None
        for port in ports:
            if not 1 <= port <= 65535:
                raise ValueError(f"Output pane port must be between 1 and 65535, got {port}.")
            try:
                self._server = _PaneServer((host, port), handler, self)
                break
            except OSError as exc:
                last_error = exc
        if self._server is None:
            if self._port_config is not None:
                message = f"Output pane port {self._port_config} on {host} is unavailable."
            elif self._port_range:
                message = f"Output pane ports {self._port_range[0]}-{self._port_range[-1]} on {host} are unavailable."
            else:
                message = "Output pane has no ports configured."
            raise OutputPanePortError(message) from last_error
        self._port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    @property
    def url(self) -> str | None:
        if self._port is None:
            return None
        host = "127.0.0.1" if self._host in ("0.0.0.0", "::", "localhost") else self._host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{self._port}/"

    @property
    def bind_host(self) -> str:
        return self._host

    def push(self, turn: PaneTurn) -> None:
        """Record a turn ({"records": [{"label", "views": [...]}, ...]}) for the pane."""
        with self._cond:
            assigned = cast(PaneTurn, dict(turn))
            assigned["id"] = self._next_id
            self._next_id += 1
            self._results.append(assigned)
            self._cond.notify_all()

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
