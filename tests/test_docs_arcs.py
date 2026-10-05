import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/docs/data/arcs-sample-tasks.json"
BUNDLE = ROOT / "docs/assets/arcs/sample-tasks.compact.json"
GENERATOR = ROOT / "scripts/docs/generate_arcs_samples.py"


def test_arcs_sample_bundle_is_current_and_compact() -> None:
    subprocess.run([sys.executable, str(GENERATOR), "--check"], check=True)
    assert BUNDLE.stat().st_size < SOURCE.stat().st_size * 0.6

    tasks = json.loads(BUNDLE.read_text())
    assert len(tasks) == 3
    for task in tasks:
        for query in task["gold_queries"]:
            assert '<span class="k">' in query["sql_html"]
            assert "query" not in query
            assert len(query["result"]["rows"]) <= (155 if task["qid"] == "004" else 10)
