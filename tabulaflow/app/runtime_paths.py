"""Runtime path helpers for CLI sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import secrets
import tempfile
import time


def _dumps_root() -> Path:
    """Per-user root for transient view dumps under the OS temp dir.

    Namespaced by uid so users on a shared box neither collide on nor read each
    other's dir; locked to 0700 (see ``ensure_dumps_dir``) so a multi-user
    ``/tmp`` can't expose dump contents. Windows has no ``getuid`` and a per-user
    temp dir already, so it stays un-namespaced there.
    """
    getuid = getattr(os, "getuid", None)
    name = f"tabulaflow-{getuid()}" if getuid is not None else "tabulaflow"
    return Path(tempfile.gettempdir()) / name


def generate_session_id() -> str:
    """Create a collision-resistant session identifier."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    pid = os.getpid()
    suffix = secrets.token_hex(3)
    return f"{timestamp}-{pid}-{suffix}"


@dataclass(frozen=True)
class RuntimePaths:
    """Derived runtime paths for a single CLI session."""

    logs_dir: Path
    trajectories_dir: Path
    data_dir: Path
    scratch_dir: Path
    workspace_db_path: Path
    history_path: Path
    cli_log_path: Path
    dumps_dir: Path

    @classmethod
    def for_session(cls, session_id: str) -> RuntimePaths:
        """Build runtime paths for the provided session id."""
        root = Path.home() / ".tabulaflow"
        session_dir = root / "sessions" / session_id
        logs_dir = session_dir / "logs"
        trajectories_dir = session_dir / "trajectories"
        data_dir = session_dir / "data"
        # Agent working area: transient files (e.g. parquet staged by the shell
        # tool before in-process ingestion) and any other intermediate work for
        # the session. Sibling of ``data/`` (which holds live connector DBs) so
        # transient blobs never mix with materialized datasets. Wiped on exit.
        scratch_dir = session_dir / "scratch"
        # Cell/table/chart dumps are transient view artifacts (open in browser,
        # look, done). Kept under the OS temp dir (not ~/.tabulaflow) for OS-level
        # cleanup, in a per-session subdir under a per-user 0700 root so a shared
        # /tmp can't expose them and sessions clean up independently.
        dumps_dir = _dumps_root() / session_id
        return cls(
            logs_dir=logs_dir,
            trajectories_dir=trajectories_dir,
            data_dir=data_dir,
            scratch_dir=scratch_dir,
            workspace_db_path=session_dir / "workspace.duckdb",
            history_path=root / "history.jsonl",
            cli_log_path=logs_dir / "cli.log",
            dumps_dir=dumps_dir,
        )


def ensure_dumps_dir(dumps_dir: Path) -> Path:
    """Create the per-session dumps dir and its per-user root, both 0700.

    0700 on the directories means no other user on a shared box can traverse in to
    read the dump files, so the files themselves need no special mode. Returns
    ``dumps_dir``. A chmod failure (e.g. an exotic filesystem) is swallowed.
    """
    for directory in (dumps_dir.parent, dumps_dir):
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.chmod(0o700)
        except OSError:
            pass
    return dumps_dir


def prune_old_dumps(max_age_seconds: float = 7 * 86400.0, *, root: Path | None = None) -> None:
    """Delete per-session dump dirs older than ``max_age_seconds``.

    Belt-and-suspenders on top of the OS's TMPDIR cleanup (no firm schedule on
    macOS) and the per-session cleanup on exit, for sessions that crashed or were
    killed. The default 7-day window covers the "left a tab open over a weekend"
    case while bounding tmp usage. Errors are swallowed so a cleanup failure never
    blocks startup.
    """
    import shutil

    root = root or _dumps_root()
    if not root.is_dir():
        return
    cutoff = time.time() - max_age_seconds
    for entry in root.iterdir():
        try:
            if not entry.is_dir() or entry.stat().st_mtime >= cutoff:
                continue
        except OSError:
            continue
        shutil.rmtree(entry, ignore_errors=True)
