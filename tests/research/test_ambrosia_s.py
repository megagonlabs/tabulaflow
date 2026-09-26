from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tabulaflow.data import SQLConnector
from tabulaflow.data.protocols import validate_global_id
from tabulaflow.research.benchmarks.ambrosia_s import AmbrosiaSDatasetLoader, _ambrosia_global_id


def test_global_id_is_stable_and_safe() -> None:
    database = "attachment/Job Postings/example"

    global_id = _ambrosia_global_id(database)

    assert global_id == _ambrosia_global_id(database)
    assert global_id != _ambrosia_global_id("attachment/Job Postings/other")
    assert global_id.startswith("ambrosia-s+")
    assert validate_global_id(global_id) == global_id


@pytest.mark.asyncio
async def test_connector_uses_stable_id_for_database_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = "attachment/Job Postings/example"
    (tmp_path / "db_list.txt").write_text(f"{database}\n")
    connector = SimpleNamespace()
    create_connector = AsyncMock(return_value=connector)
    monkeypatch.setattr(SQLConnector, "from_url_async", create_connector)
    loader = AmbrosiaSDatasetLoader(directory=str(tmp_path))

    connectors = await loader.get_db_connectors_async("test")

    assert connectors[database] is connector
    call = create_connector.await_args
    assert call is not None
    assert call.kwargs["display_name"] == database
    assert call.kwargs["global_id"] == _ambrosia_global_id(database)
