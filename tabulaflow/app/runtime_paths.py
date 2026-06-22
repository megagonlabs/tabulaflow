"""Runtime path helpers for CLI sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
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
        # Cell and table dumps are transient view artifacts (open in
        # browser, look, done). Keep them out of ~/.tabulaflow so they get
        # OS-level cleanup, and skip the per-session subdir to keep paths
        # short — uniqueness comes from the random per-file suffix.
        dumps_dir = Path(tempfile.gettempdir()) / "tabulaflow"
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


def prune_old_dumps(max_age_seconds: float = 7 * 86400.0) -> None:
    """Delete cell-, table-, and chart-dump artifacts older than ``max_age_seconds``.

    Cleans up three kinds of entries in the shared dumps dir:
      - ``C_*`` cell dumps (single files)
      - ``T_*`` table dumps (an ``.html`` file plus a sibling directory of
        spilled media blobs sharing the same stem)
      - ``V_*`` chart dumps (single ``.html`` files)

    Belt-and-suspenders on top of the OS's TMPDIR cleanup, which on macOS
    has no firm schedule. The default 7-day window covers the common
    "left a browser tab open over a weekend / short trip" case while
    still bounding accumulated tmp usage. Errors are swallowed so a
    cleanup failure never blocks app startup.
    """
    import shutil

    tmp_root = Path(tempfile.gettempdir()) / "tabulaflow"
    if not tmp_root.is_dir():
        return
    cutoff = time.time() - max_age_seconds
    for entry in tmp_root.iterdir():
        name = entry.name
        if not (name.startswith("C_") or name.startswith("T_") or name.startswith("V_")):
            continue
        try:
            if entry.stat().st_mtime >= cutoff:
                continue
        except OSError:
            continue
        try:
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink()
        except OSError:
            continue
