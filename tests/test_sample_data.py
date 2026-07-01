from __future__ import annotations

import sqlite3
import json
from importlib.resources import as_file, files

from tabulaflow.app.sample_data import SAMPLE_TABLES


def test_sample_data_includes_raw_nyc_taxi_zones() -> None:
    assert "nyc_taxi_zones" in SAMPLE_TABLES
    with as_file(files("tabulaflow.app.assets.samples").joinpath("sample.sqlite")) as db_path:
        conn = sqlite3.connect(db_path)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(nyc_taxi_zones)")]
            assert columns == ["the_geom", "shape_leng", "shape_area", "zone", "locationid", "borough"]
            assert conn.execute("SELECT COUNT(*) FROM nyc_taxi_zones").fetchone()[0] == 263
            geom = conn.execute("SELECT the_geom FROM nyc_taxi_zones LIMIT 1").fetchone()[0]
            assert json.loads(geom)["type"] == "MultiPolygon"
        finally:
            conn.close()
