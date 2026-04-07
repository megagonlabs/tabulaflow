"""Runtime path helpers for CLI sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import secrets


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
    history_path: Path
    cli_log_path: Path

    @classmethod
    def for_session(cls, session_id: str) -> RuntimePaths:
        """Build runtime paths for the provided session id."""
        root = Path.home() / ".mintq"
        session_dir = root / "sessions" / session_id
        logs_dir = session_dir / "logs"
        trajectories_dir = session_dir / "trajectories"
        return cls(
            logs_dir=logs_dir,
            trajectories_dir=trajectories_dir,
            history_path=root / "history",
            cli_log_path=logs_dir / "cli.log",
        )
