"""Subprocess runner for loader workers.

Each loader (``files.py``, ``huggingface.py``, etc.) ends with a worker
``__main__`` block that reads a JSON payload from stdin and performs its
DuckDB load.  This module spawns those workers and integrates them with
asyncio cancellation: when the calling task is cancelled, the subprocess
is terminated, and OS-level cleanup releases any open file handles
(DuckDB locks, pending native I/O) — the reliable alternative to trying
to interrupt long-running sync C calls in-process.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any


async def run_loader_subprocess(
    worker_module: str,
    payload: dict[str, Any],
    *,
    terminate_grace_seconds: float = 2.0,
) -> None:
    """Run ``python -m <worker_module>`` in a subprocess, piping ``payload``
    as JSON on stdin, and await its exit.

    Args:
        worker_module: Dotted module path, e.g.
            ``"mintq.db_connector.loaders.files"``.  The module's
            ``__main__`` reads the payload from stdin.
        payload: JSON-serialisable payload.
        terminate_grace_seconds: Wait after ``terminate()`` before escalating
            to ``kill()``.

    Raises:
        RuntimeError: If the subprocess exits with a non-zero status.
    """
    payload_bytes = json.dumps(payload).encode("utf-8")
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        worker_module,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _stdout, stderr_data = await proc.communicate(payload_bytes)
    except asyncio.CancelledError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=terminate_grace_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        raise
    if proc.returncode != 0:
        msg = stderr_data.decode("utf-8", errors="replace").strip() or "no error output"
        raise RuntimeError(f"{worker_module} subprocess failed: {msg}")
