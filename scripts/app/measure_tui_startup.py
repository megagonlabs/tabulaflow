#!/usr/bin/env python3
"""Measure TUI startup latency: from launching ``uv run tabulaflow`` to the
moment the banner is actually rendered on screen.

Runs the real command inside a pseudo-terminal (so Textual renders as it would in
a real terminal) and stops the clock the instant the banner text appears in the
output. Reports the end-to-end time plus a ``uv run`` baseline so you can see how
much is launcher/interpreter overhead vs. the app itself.

Run with the *system* python (NOT ``uv run``), so it can time the uv subprocess:

    python3 scripts/app/measure_tui_startup.py [runs]

The first run is cold (compiles .pyc); later runs reflect steady-state launches.
Version-agnostic — measures whatever is currently checked out, so you can compare
branches/stashes by re-running.
"""

from __future__ import annotations

import fcntl
import argparse
import os
import pty
import re
import select
import struct
import subprocess
import termios
import time

# The launch command a user types. ``tabulaflow`` is a single-command typer app
# (no subcommand); passing ``-m`` avoids the no-args help screen.
BASELINE_CMD = ["uv", "run", "python", "-c", "pass"]

# The banner panel renders "Type /help for commands, /exit to exit". Match that
# (ANSI-stripped first so styling can't split it). Avoid bare "tabulaflow" — it
# shows up in early usage/error text long before the banner.
_BANNER_RE = re.compile(rb"to exit|help for commands", re.IGNORECASE)
_ANSI_RE = re.compile(rb"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")

TIMEOUT = 40.0  # seconds before giving up on a single run


def _strip_ansi(b: bytes) -> bytes:
    return _ANSI_RE.sub(b"", b)


def measure_to_banner(command: list[str]) -> tuple[float | None, bytes]:
    """Spawn the TUI in a pty; return (seconds-to-banner | None, captured output)."""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))
    env = {**os.environ, "TERM": "xterm-256color"}

    t0 = time.perf_counter()
    proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, env=env, close_fds=True)
    os.close(slave)

    buf = b""
    elapsed: float | None = None
    deadline = t0 + TIMEOUT
    try:
        while time.perf_counter() < deadline:
            ready, _, _ = select.select([master], [], [], 0.05)
            if ready:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                buf += data
                if _BANNER_RE.search(_strip_ansi(buf)):
                    elapsed = time.perf_counter() - t0
                    break
            elif proc.poll() is not None:
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        os.close(master)
    return elapsed, buf


def measure_baseline() -> float:
    """Time ``uv run python -c pass`` — uv resolution + interpreter startup, no app."""
    t0 = time.perf_counter()
    subprocess.run(BASELINE_CMD, capture_output=True)
    return time.perf_counter() - t0


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure time from TUI launch until the welcome banner appears.")
    parser.add_argument("runs", type=int, nargs="?", default=4)
    parser.add_argument("--model", default="openai-responses:gpt-5.4")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("runs must be positive")

    command = ["uv", "run", "tabulaflow", "-m", args.model]
    print(f"command: {' '.join(command)}")

    base = measure_baseline()  # warm baseline (after this, uv env is resolved/cached)
    base = measure_baseline()
    print(f"baseline (uv run python -c pass): {base:.2f}s  [launcher + interpreter overhead]\n")

    warm: list[float] = []
    for i in range(args.runs):
        elapsed, buf = measure_to_banner(command)
        label = "cold" if i == 0 else "warm"
        if elapsed is None:
            tail = _strip_ansi(buf)[-400:].decode("utf-8", "replace").strip()
            print(f"  run {i + 1} ({label}): BANNER NOT DETECTED in {TIMEOUT:.0f}s")
            print(f"            last output: …{tail!r}")
        else:
            app = elapsed - base
            print(f"  run {i + 1} ({label}): {elapsed:.2f}s to banner  (≈{base:.2f}s launcher + {app:.2f}s app)")
            if i > 0:
                warm.append(elapsed)

    if warm:
        warm.sort()
        med = warm[len(warm) // 2]
        print(f"\nwarm runs: min={min(warm):.2f}s  median={med:.2f}s  (n={len(warm)})")
        print(f"  of which ≈{base:.2f}s is uv/interpreter; ≈{med - base:.2f}s is import + render")


if __name__ == "__main__":
    main()
