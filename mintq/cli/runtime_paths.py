"""Runtime path helpers for CLI sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
import shutil
from pathlib import Path
import secrets
import tempfile
import time


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
    workspace_db_path: Path
    history_path: Path
    cli_log_path: Path
    cell_dumps_dir: Path

    @classmethod
    def for_session(cls, session_id: str) -> RuntimePaths:
        """Build runtime paths for the provided session id."""
        root = Path.home() / ".mintq"
        session_dir = root / "sessions" / session_id
        logs_dir = session_dir / "logs"
        trajectories_dir = session_dir / "trajectories"
        data_dir = session_dir / "data"
        # Cell dumps are transient view artifacts (open in browser, look,
        # done). Keep them out of ~/.mintq so they get OS-level cleanup
        # instead of accumulating across sessions.
        cell_dumps_dir = Path(tempfile.gettempdir()) / "mintq" / session_id
        return cls(
            logs_dir=logs_dir,
            trajectories_dir=trajectories_dir,
            data_dir=data_dir,
            workspace_db_path=session_dir / "workspace.duckdb",
            history_path=root / "history.jsonl",
            cli_log_path=logs_dir / "cli.log",
            cell_dumps_dir=cell_dumps_dir,
        )


def prune_old_cell_dumps(current_session_id: str, max_age_seconds: float = 7 * 86400.0) -> None:
    """Delete cell-dump session dirs older than ``max_age_seconds``.

    Belt-and-suspenders on top of the OS's TMPDIR cleanup, which on macOS
    has no firm schedule. The default 7-day window covers the common
    "left a browser tab open over a weekend / short trip" case while still
    bounding accumulated tmp usage. The current session is always
    preserved. Errors are swallowed so a cleanup failure never blocks app
    startup.
    """
    tmp_root = Path(tempfile.gettempdir()) / "mintq"
    if not tmp_root.is_dir():
        return
    cutoff = time.time() - max_age_seconds
    for session_dir in tmp_root.iterdir():
        if not session_dir.is_dir() or session_dir.name == current_session_id:
            continue
        try:
            if session_dir.stat().st_mtime < cutoff:
                shutil.rmtree(session_dir, ignore_errors=True)
        except OSError:
            continue
