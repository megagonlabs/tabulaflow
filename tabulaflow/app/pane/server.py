"""Embedded HTTP server that mirrors the agent's cited results in a live browser pane.

A stdlib ``http.server`` running in a daemon thread serves the single-page pane,
structured record-data files written to the session dumps dir, and a Server-Sent
Events stream of turn manifests. Session data routes are protected by a
per-session URL token; bundled assets are public and cacheable.

The pane is an *additive, output-only* surface: the TUI remains the primary
interface, and every failure here is swallowed so it can never block a chat turn.
"""

from __future__ import annotations

import functools
import hashlib
import http.server
import json
import logging
import posixpath
import secrets
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast
from urllib.parse import unquote, urlsplit, urlunsplit

from tabulaflow.app.pane.types import CARD_ID_PREFIX, PaneTurn
from tabulaflow.app.theme import GITHUB_SLUG, GITHUB_URL

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PANE_PORT_START = 61111
DEFAULT_OUTPUT_PANE_PORT_END = 61130
DEFAULT_OUTPUT_PANE_PORTS = tuple(range(DEFAULT_OUTPUT_PANE_PORT_START, DEFAULT_OUTPUT_PANE_PORT_END + 1))
DEFAULT_OUTPUT_PANE_HOST = "127.0.0.1"
_OUTPUT_PANE_TOKEN_BYTES = 6

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


def _load_pane_html() -> str:
    from importlib.resources import files

    base = files("tabulaflow.app.pane.assets.ui")
    html = base.joinpath("index.html").read_text(encoding="utf-8")
    css = base.joinpath("pane.css").read_text(encoding="utf-8")
    module_hash = hashlib.sha256()
    for rel in (
        "pane.js",
        "render/shared.js",
        "render/table.js",
        "render/chart.js",
        "render/map.js",
        "render/graph.js",
        "render/query.js",
    ):
        module_hash.update(base.joinpath(rel).read_bytes())
    pane_version = module_hash.hexdigest()[:12]
    return html.replace("__PANE_CSS__", css).replace("__PANE_VERSION__", pane_version).replace("__BANNER__", _BANNER)


_PANE_HTML = _load_pane_html()

_INVALID_PANE_URL_HTML = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    "<title>Output pane URL incomplete</title>"
    "<style>"
    "html{color-scheme:dark;background:#0f1117;color:#e4e4e7;font-family:system-ui,sans-serif}"
    "body{margin:0;min-height:100vh;display:grid;place-items:center}"
    "main{max-width:36rem;padding:2rem;line-height:1.5}"
    "h1{font-size:1rem;margin:0 0 .5rem}"
    "p{margin:0;color:#a1a1aa}"
    "</style></head><body><main>"
    "<h1>Output pane URL is incomplete.</h1>"
    "<p>Open the full URL shown in the tabulaflow terminal.</p>"
    "</main></body></html>"
)


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
    """Serves the pane page, protected session data, and bundled assets."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API name)
        if self.path.startswith("/assets/"):
            self._serve_asset(self.path[len("/assets/") :])
            return
        assert isinstance(self.server, _PaneServer)
        pane = self.server.pane
        session_path = pane._session_path(self.path)
        if session_path is None:
            self._send_invalid_pane_url_html()
            return
        if session_path in ("", "index.html"):
            self._send_pane_html()
            return
        if session_path == "events":
            self._serve_events()
            return
        if session_path.endswith(".data.json") or "/" in session_path:
            self._serve_pane_file(session_path)
            return
        self.send_error(404)

    def _send_pane_html(self) -> None:
        body = _PANE_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_invalid_pane_url_html(self) -> None:
        body = _INVALID_PANE_URL_HTML.encode("utf-8")
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
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
        """Serve bundled browser assets."""
        from importlib.resources import files

        clean = rel.split("?", 1)[0]
        parts = [p for p in clean.split("/") if p]
        if not parts or ".." in parts:
            self.send_error(404)
            return
        resource = files("tabulaflow.app.pane.assets")
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
        elif clean.endswith(".json") or clean.endswith(".geojson"):
            ctype = "application/json; charset=utf-8"
        elif clean.endswith(".png"):
            ctype = "image/png"
        else:
            ctype = "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if clean.startswith("ui/") or clean.endswith(".json") or clean.endswith(".geojson"):
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(data)

    def _serve_pane_file(self, rel: str) -> None:
        """Serve explicitly allowed session artifact files."""
        assert isinstance(self.server, _PaneServer)
        pane = self.server.pane
        clean = posixpath.normpath(unquote(rel.split("?", 1)[0])).lstrip("/")
        if clean in ("", ".") or clean.startswith("../") or clean == "..":
            self.send_error(404)
            return
        allowed = clean.startswith(CARD_ID_PREFIX) and (clean.endswith(".data.json") or "/" in clean)
        if not allowed:
            self.send_error(404)
            return
        path = pane._pane_dir / clean
        try:
            resolved = path.resolve()
            root = pane._pane_dir.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            self.send_error(404)
            return
        if not resolved.is_file():
            self.send_error(404)
            return
        try:
            data = resolved.read_bytes()
        except OSError:
            self.send_error(404)
            return
        if clean.endswith(".json"):
            ctype = "application/json; charset=utf-8"
        elif clean.endswith(".svg"):
            ctype = "image/svg+xml"
        elif clean.endswith(".png"):
            ctype = "image/png"
        elif clean.endswith(".jpg") or clean.endswith(".jpeg"):
            ctype = "image/jpeg"
        elif clean.endswith(".gif"):
            ctype = "image/gif"
        elif clean.endswith(".webp"):
            ctype = "image/webp"
        elif clean.endswith(".pdf"):
            ctype = "application/pdf"
        elif clean.endswith(".wav"):
            ctype = "audio/wav"
        elif clean.endswith(".mp3"):
            ctype = "audio/mpeg"
        elif clean.endswith(".mp4"):
            ctype = "video/mp4"
        elif clean.endswith(".webm"):
            ctype = "video/webm"
        else:
            ctype = "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        """Silence request logging — stray stderr would corrupt the TUI."""


class OutputPanePortError(RuntimeError):
    """Raised when the output pane cannot bind its configured loopback port(s)."""


class OutputPane:
    """An HTTP server plus browser tab showing cited results as they arrive."""

    def __init__(
        self,
        pane_dir: Path,
        *,
        host: str = DEFAULT_OUTPUT_PANE_HOST,
        port: int | None = None,
        port_range: Sequence[int] = DEFAULT_OUTPUT_PANE_PORTS,
        public_url: str | None = None,
        token: str | None = None,
    ) -> None:
        self._pane_dir = pane_dir
        self._manifest_path = pane_dir / "turns.jsonl"
        self._host = host.strip()
        if not self._host:
            raise ValueError("Output pane host cannot be empty.")
        self._public_url = public_url.strip() if public_url is not None else None
        if self._public_url == "":
            raise ValueError("Output pane public URL cannot be empty.")
        self._public_path_parts: tuple[str, ...] = ()
        if self._public_url is not None:
            public_parts = urlsplit(self._public_url)
            if not public_parts.scheme or not public_parts.netloc:
                raise ValueError(f"Output pane public URL must be absolute, got {self._public_url!r}.")
            if public_parts.query or public_parts.fragment:
                raise ValueError("Output pane public URL cannot include query parameters or a fragment.")
            self._public_path_parts = tuple(unquote(part) for part in public_parts.path.split("/") if part)
        self._token = token or secrets.token_urlsafe(_OUTPUT_PANE_TOKEN_BYTES)
        if not self._token:
            raise ValueError("Output pane token cannot be empty.")
        self._port_config = port
        self._port_range = tuple(port_range)
        self._results: list[PaneTurn] = []
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._next_id = 0
        self._loaded = False
        self._server: _PaneServer | None = None
        self._port: int | None = None
        self._browser_opened = False

    def start(self) -> None:
        """Bind the pane server and serve it in a daemon thread.

        With no explicit port, the pane takes the first available port from the
        stable default range. An explicit port is strict and fails if occupied.
        """
        with self._cond:
            self._load_manifest_locked()
        host = self._host
        handler = functools.partial(_Handler, directory=str(self._pane_dir))
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
        if self._public_url is not None:
            return self._tokenized_url(self._public_url)
        host = "127.0.0.1" if self._host in ("0.0.0.0", "::", "localhost") else self._host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return self._tokenized_url(f"http://{host}:{self._port}/")

    @property
    def bind_host(self) -> str:
        return self._host

    @property
    def token(self) -> str:
        return self._token

    def _tokenized_url(self, base_url: str) -> str:
        """Append the session token as the final path segment of ``base_url``."""
        parsed = urlsplit(base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Output pane public URL must be absolute, got {base_url!r}.")
        path = parsed.path.rstrip("/")
        token_path = f"{path}/{self._token}/" if path else f"/{self._token}/"
        return urlunsplit((parsed.scheme, parsed.netloc, token_path, "", ""))

    def _session_path(self, request_path: str) -> str | None:
        """Return the token-scoped relative path, or None for an invalid token."""
        clean = request_path.split("?", 1)[0]
        parts = [unquote(part) for part in clean.split("/") if part]
        if self._public_path_parts and tuple(parts[: len(self._public_path_parts)]) == self._public_path_parts:
            parts = parts[len(self._public_path_parts) :]
        if not parts:
            return None
        if not secrets.compare_digest(parts[0], self._token):
            return None
        if len(parts) == 1:
            return ""
        return "/".join(parts[1:])

    def push(self, turn: PaneTurn) -> None:
        """Record a turn ({"cards": [{"label", "views": [...]}, ...]}) for the pane."""
        with self._cond:
            self._load_manifest_locked()
            assigned = cast(PaneTurn, dict(turn))
            assigned["id"] = self._next_id
            self._next_id += 1
            self._results.append(assigned)
            self._append_manifest_locked(assigned)
            self._cond.notify_all()

    def _load_manifest_locked(self) -> None:
        """Load persisted pane turns once. Caller must hold ``_cond``."""
        if self._loaded:
            return
        self._loaded = True
        max_id = -1
        try:
            lines = self._manifest_path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return
        except OSError:
            return
        results: list[PaneTurn] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            turn = cast(PaneTurn, raw)
            turn_id = turn.get("id")
            if not isinstance(turn_id, int):
                turn_id = max_id + 1
                turn["id"] = turn_id
            max_id = max(max_id, turn_id)
            results.append(turn)
        self._results = results
        self._next_id = max_id + 1

    def _append_manifest_locked(self, turn: PaneTurn) -> None:
        """Persist one turn manifest. Caller must hold ``_cond``."""
        try:
            self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with self._manifest_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(turn, ensure_ascii=False) + "\n")
        except OSError:
            logger.debug("output pane manifest write failed", exc_info=True)

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
