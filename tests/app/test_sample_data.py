from __future__ import annotations

import io
import json
import sqlite3
from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from tabulaflow.core.media import detect_media
from tabulaflow.app.sample_data import SAMPLE_TABLES, _copy_if_changed


def test_copy_sample_data_refreshes_same_size_changes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "shared" / "sample.sqlite"
    source.write_bytes(b"new")
    destination.parent.mkdir()
    destination.write_bytes(b"old")

    _copy_if_changed(source, destination)

    assert destination.read_bytes() == b"new"


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


def test_sample_data_includes_realistic_expense_media() -> None:
    assert "expense_documents" in SAMPLE_TABLES
    with as_file(files("tabulaflow.app.assets.samples").joinpath("sample.sqlite")) as db_path:
        conn = sqlite3.connect(db_path)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(expense_documents)")]
            assert columns == ["document_id", "filename", "content"]
            rows = conn.execute("SELECT filename, content FROM expense_documents ORDER BY document_id").fetchall()
        finally:
            conn.close()

    assert len(rows) == 5
    detected = [detect_media(content) for _, content in rows]
    assert [item.media_type if item else None for item in detected] == [
        "image/png",
        "image/png",
        "image/png",
        "application/pdf",
        "application/pdf",
    ]
    for _, content in rows[:3]:
        with Image.open(io.BytesIO(content)) as image:
            assert image.size == (1000, 1500)
            image.verify()
    for _, content in rows[3:]:
        assert len(PdfReader(io.BytesIO(content)).pages) == 1
