import json
import tempfile
from pathlib import Path

import pytest

from mintq.datahub.cypherbench import CypherBenchDatasetLoader


@pytest.mark.asyncio
async def test_cypherbench_get_tasks_from_json() -> None:
    sample = [
        {
            "qid": "q-1",
            "graph": "nba",
            "gold_cypher": "MATCH (n:Player) RETURN n.name LIMIT 1",
            "nl_question": "One player name?",
            "answer_json": "[]",
            "from_template": None,
        }
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.json"
        path.write_text(json.dumps(sample), encoding="utf-8")
        loader = CypherBenchDatasetLoader(directory=tmp)
        tasks = await loader.get_tasks_async("test", databases=["nba"])
        assert len(tasks) == 1
        assert tasks[0].qid == "q-1"
        assert tasks[0].db == "nba"
        assert tasks[0].gold_query.query == "MATCH (n:Player) RETURN n.name LIMIT 1"
        assert tasks[0].extra_info["cypherbench"]["from_template"] is None


def test_cypherbench_get_databases() -> None:
    loader = CypherBenchDatasetLoader(directory="unused")
    assert "nba" in loader.get_databases("test")
    assert "art" in loader.get_databases("train")
