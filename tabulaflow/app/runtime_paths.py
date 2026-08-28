"""Runtime path helpers for CLI sessions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
import string

_SESSION_ID_ALPHABET = string.digits + string.ascii_lowercase
_SESSION_ID_LENGTH = 6


def generate_session_id() -> str:
    """Create a collision-resistant session identifier."""
    return "".join(secrets.choice(_SESSION_ID_ALPHABET) for _ in range(_SESSION_ID_LENGTH))


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
    pane_dir: Path

    @property
    def session_dir(self) -> Path:
        """Root directory for this session's files."""
        return self.workspace_db_path.parent

    @property
    def session_id(self) -> str:
        """Identifier of this session."""
        return self.session_dir.name

    @classmethod
    def create(cls) -> RuntimePaths:
        """Atomically reserve runtime paths for a new session."""
        sessions_dir = Path.home() / ".tabulaflow" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        while True:
            paths = cls.for_session(generate_session_id())
            try:
                paths.session_dir.mkdir(mode=0o700)
            except FileExistsError:
                continue
            return paths

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
        # Card data and spilled media served by the browser pane during this session.
        pane_dir = session_dir / "pane"
        return cls(
            logs_dir=logs_dir,
            trajectories_dir=trajectories_dir,
            data_dir=data_dir,
            scratch_dir=scratch_dir,
            workspace_db_path=session_dir / "workspace.duckdb",
            history_path=root / "history.jsonl",
            cli_log_path=logs_dir / "cli.log",
            pane_dir=pane_dir,
        )


def ensure_pane_dir(pane_dir: Path) -> Path:
    """Create the per-session pane artifact dir, locked to 0700 where possible.

    0700 on the session and pane directories means no other user on a shared box
    can traverse in to read pane data. Returns ``pane_dir``. A chmod failure
    (e.g. an exotic filesystem) is swallowed.
    """
    for directory in (pane_dir.parent, pane_dir):
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.chmod(0o700)
        except OSError:
            pass
    return pane_dir
