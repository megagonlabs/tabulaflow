"""Runtime path helpers for CLI sessions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
import string

from tabulaflow._paths import DEFAULT_HOME_DIR

_SESSION_ID_ALPHABET = string.digits + string.ascii_lowercase
_SESSION_ID_LENGTH = 6


def generate_session_id() -> str:
    """Create a collision-resistant session identifier."""
    return "".join(secrets.choice(_SESSION_ID_ALPHABET) for _ in range(_SESSION_ID_LENGTH))


@dataclass(frozen=True)
class RuntimePaths:
    """Derived runtime paths for a single CLI session."""

    home_dir: Path
    session_id: str

    @property
    def session_dir(self) -> Path:
        """Root directory for this session's files."""
        return self.home_dir / "sessions" / self.session_id

    @property
    def logs_dir(self) -> Path:
        """Directory for session logs."""
        return self.session_dir / "logs"

    @property
    def trajectories_dir(self) -> Path:
        """Directory for agent trajectory records."""
        return self.session_dir / "trajectories"

    @property
    def data_dir(self) -> Path:
        """Directory for session-local data caches."""
        return self.session_dir / "data"

    @property
    def scratch_dir(self) -> Path:
        """Directory for transient agent files."""
        return self.session_dir / "scratch"

    @property
    def workspace_db_path(self) -> Path:
        """Path to the writable workspace database."""
        return self.session_dir / "workspace.duckdb"

    @property
    def history_path(self) -> Path:
        """Path to the global TUI input history."""
        return self.home_dir / "history.jsonl"

    @property
    def cli_log_path(self) -> Path:
        """Path to this session's CLI log."""
        return self.logs_dir / "cli.log"

    @property
    def pane_dir(self) -> Path:
        """Directory for ephemeral browser-pane artifacts."""
        return self.session_dir / "pane"

    @classmethod
    def create(cls, *, home_dir: Path | None = None) -> RuntimePaths:
        """Atomically reserve runtime paths for a new session."""
        home_dir = home_dir if home_dir is not None else DEFAULT_HOME_DIR
        sessions_dir = home_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        while True:
            paths = cls(home_dir=home_dir, session_id=generate_session_id())
            try:
                paths.session_dir.mkdir(mode=0o700)
            except FileExistsError:
                continue
            return paths

    @classmethod
    def for_session(cls, session_id: str, *, home_dir: Path | None = None) -> RuntimePaths:
        """Build runtime paths for the provided session id."""
        return cls(
            home_dir=home_dir if home_dir is not None else DEFAULT_HOME_DIR,
            session_id=session_id,
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
