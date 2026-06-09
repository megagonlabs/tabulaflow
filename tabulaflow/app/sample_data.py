"""Bundled sample database.

A single SQLite file (``app/assets/samples/sample.sqlite``) with three example
tables — ``bank_transactions``, ``product_reviews``, and ``model_eval_results``
— backing the welcome-banner examples. It auto-connects when the app launches
with no user data, so a first-time user can run the examples without supplying
anything.

Regenerate the file with ``scripts/gen_sample_db.py``.
"""

from __future__ import annotations

import os
import shutil
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.session import WORKSPACE_ALIAS

if TYPE_CHECKING:
    from tabulaflow.app.session import SessionState

SAMPLE_ALIAS = "sample_data"
SAMPLE_TABLES = ("bank_transactions", "product_reviews", "model_eval_results")
_RESOURCE = "tabulaflow.app.assets.samples"
_FILENAME = "sample.sqlite"
# Shared per-user location (not per-session): copy once, reuse across sessions.
_SHARED_DIR = Path.home() / ".tabulaflow" / "sample_data"


def materialize_sample_db() -> Path:
    """Return a real, writable path to the sample DB, copying it once if needed.

    The copy lives in a shared per-user dir (``~/.tabulaflow/sample_data``) rather
    than each session's dir, so it isn't duplicated per session. It's refreshed
    only when the bundled file changes (size differs), so a new app version's
    schema is picked up. A copy (vs opening the packaged file in place) is
    required: the package file may be read-only / inside a zipped wheel, and the
    SQLite connector opens read-write at the driver level.
    """
    dest = _SHARED_DIR / _FILENAME
    with as_file(files(_RESOURCE).joinpath(_FILENAME)) as src:
        if not dest.exists() or dest.stat().st_size != Path(src).stat().st_size:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
    return dest


def has_user_data(session: SessionState) -> bool:
    """Whether any database besides the built-in workspace is connected."""
    return any(alias != WORKSPACE_ALIAS for alias in session.registry.list_aliases())


async def autoconnect_sample(session: SessionState) -> bool:
    """Connect the bundled sample DB under ``SAMPLE_ALIAS`` when no user data exists.

    Returns True if it was connected, False if skipped (user data already present
    or the sample is already registered).
    """
    if has_user_data(session) or session.registry.has(SAMPLE_ALIAS):
        return False

    from tabulaflow.core.db_connector.sql_conn import SQLConnector

    path = os.path.abspath(materialize_sample_db())
    connector = await SQLConnector.from_url_async(
        global_id=f"cli+{SAMPLE_ALIAS}",
        url=f"sqlite+aiosqlite:///{path}",
        db_name=SAMPLE_ALIAS,
        read_only=True,
        # The sample is tiny (instant to introspect) and its schema can change
        # between versions under the same global_id — caching would risk serving a
        # stale schema for no speed benefit.
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    session.registry.register(SAMPLE_ALIAS, connector)
    session.register_source(("sample", _FILENAME), SAMPLE_ALIAS)
    session.chat_agent.note_event(
        f"sample data is connected as `{SAMPLE_ALIAS}` so the welcome examples are runnable "
        f"(tables: {', '.join(SAMPLE_TABLES)}). It is placeholder demo data and will be removed "
        "automatically as soon as the user connects a data source of their own."
    )
    return True
