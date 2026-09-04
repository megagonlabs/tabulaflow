"""Tests for browser-pane table payloads."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, cast

import pandas as pd

from tabulaflow.app.pane.contract import TableCardData
from tabulaflow.app.pane.tables import build_table_data


PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PDF_MAGIC = b"%PDF-1.7\n" + b"\x00" * 32


def _payload_rows(payload: TableCardData) -> list[dict[str, Any]]:
    dataset = cast(dict[str, Any], payload["dataset"])
    return cast(list[dict[str, Any]], dataset["rows"])


def _payload_table(payload: TableCardData) -> dict[str, Any]:
    return cast(dict[str, Any], payload["table"])


class TestBuildTableData:
    def test_serializes_rows_nulls_and_metadata(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"name": ["valid", None], "score": [10.0, None]})

        payload = build_table_data(df, asset_stem="card_table", output_dir=tmp_path)

        assert _payload_rows(payload) == [{"c0": "valid", "c1": 10.0}, {"c0": None, "c1": None}]
        table = _payload_table(payload)
        assert table["meta"] == "2 rows · 2 columns"
        assert table["columns"][1]["role"] == "number"

    def test_serializes_empty_table(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"customer": pd.Series(dtype="object"), "value": pd.Series(dtype="int64")})

        payload = build_table_data(df, asset_stem="card_empty", output_dir=tmp_path)

        assert _payload_rows(payload) == []
        assert _payload_table(payload)["meta"] == "0 rows · 2 columns"

    def test_renders_image_column_inline(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"img": [PNG_MAGIC, PNG_MAGIC], "name": ["a", "b"]})
        payload = build_table_data(df, asset_stem="card_abc", output_dir=tmp_path)

        rows = _payload_rows(payload)
        table = _payload_table(payload)
        assert rows[0]["c0"]["src"].startswith("data:image/png;base64,")
        assert table["columns"][0]["role"] == "media"
        assert not (tmp_path / "card_abc").exists()

    def test_detects_media_type_per_cell(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"content": [PNG_MAGIC, PNG_MAGIC, PNG_MAGIC, PDF_MAGIC, PDF_MAGIC]})

        payload = build_table_data(df, asset_stem="card_mixed_media", output_dir=tmp_path)

        rows = _payload_rows(payload)
        assert [row["c0"]["mime"] for row in rows] == [
            "image/png",
            "image/png",
            "image/png",
            "application/pdf",
            "application/pdf",
        ]
        pdf_paths = [tmp_path / row["c0"]["src"] for row in rows[3:]]
        assert all(path.suffix == ".pdf" for path in pdf_paths)
        assert [path.read_bytes() for path in pdf_paths] == [PDF_MAGIC, PDF_MAGIC]

    def test_media_column_preserves_non_media_cells(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"content": [PNG_MAGIC, PNG_MAGIC, PNG_MAGIC, "caption", b"unknown"]})

        payload = build_table_data(df, asset_stem="card_media_text", output_dir=tmp_path)

        rows = _payload_rows(payload)
        assert _payload_table(payload)["columns"][0]["role"] == "media"
        assert rows[3]["c0"] == "caption"
        assert rows[4]["c0"] == "<binary: 7 bytes>"

    def test_data_uri_uses_detected_media_type(self, tmp_path: Path) -> None:
        encoded = base64.b64encode(PNG_MAGIC).decode("ascii")
        data_uri = f"data:application/pdf;base64,{encoded}"

        payload = build_table_data(
            pd.DataFrame({"content": [data_uri]}),
            asset_stem="card_data_uri",
            output_dir=tmp_path,
        )

        cell = _payload_rows(payload)[0]["c0"]
        assert cell["mime"] == "image/png"
        assert cell["src"].startswith("data:image/png;base64,")

    def test_spills_large_blobs(self, tmp_path: Path) -> None:
        big_png = PNG_MAGIC + b"\x00" * (300 * 1024)
        df = pd.DataFrame({"img": [big_png]})
        payload = build_table_data(df, asset_stem="card_xyz", output_dir=tmp_path, inline_cap=256 * 1024)

        sib_dir = tmp_path / "card_xyz"
        assert sib_dir.is_dir()
        spilled = list(sib_dir.glob("*.png"))
        assert len(spilled) == 1
        assert spilled[0].read_bytes() == big_png
        rows = _payload_rows(payload)
        assert rows[0]["c0"]["src"].startswith(f"./{sib_dir.name}/")
        assert not rows[0]["c0"]["src"].startswith("data:image/png;base64,")

    def test_hf_struct_image_column_rendered(self, tmp_path: Path) -> None:
        """DuckDB returns HF Image columns as ``{"bytes": <png>, "path": ...}`` dicts.

        Regression: the sniffer only handled raw bytes / base64 strings, so HF
        image columns (e.g. the CIFAR-10 cache) rendered as JSON text instead
        of inline images.
        """
        cell = {"bytes": PNG_MAGIC, "path": None}
        df = pd.DataFrame({"img": [cell, cell, cell], "label": [1, 2, 3]})
        payload = build_table_data(df, asset_stem="card_hfimg", output_dir=tmp_path)

        rows = _payload_rows(payload)
        assert rows[0]["c0"]["src"].startswith("data:image/png;base64,")

    def test_base64_string_column_rendered(self, tmp_path: Path) -> None:
        png_b64 = base64.b64encode(PNG_MAGIC + b"\x00" * 64).decode("ascii")
        df = pd.DataFrame({"img_b64": [png_b64, png_b64]})
        payload = build_table_data(df, asset_stem="card_b64", output_dir=tmp_path)

        rows = _payload_rows(payload)
        assert rows[0]["c0"]["src"].startswith("data:image/png;base64,")

    def test_row_cap_truncates(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"n": list(range(1000))})
        payload = build_table_data(df, asset_stem="card_cap", output_dir=tmp_path, max_rows=10)

        table = _payload_table(payload)
        assert table["meta"] == "showing 10 of 1,000 rows · 1 column"
        assert table["truncatedRows"] == 990

    def test_max_height_is_preserved(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        payload = build_table_data(df, asset_stem="card_short_pane", output_dir=tmp_path, max_height=640)

        assert _payload_table(payload)["maxHeight"] == 640

    def test_mixed_column_not_treated_as_media(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"col": [PNG_MAGIC, "plain string", 42, None, b"random"]})
        payload = build_table_data(df, asset_stem="card_mix", output_dir=tmp_path)

        assert _payload_table(payload)["columns"][0]["role"] == "text"

    def test_numeric_column_gets_number_role(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        payload = build_table_data(df, asset_stem="card_assets", output_dir=tmp_path)

        assert _payload_table(payload)["columns"][0]["role"] == "number"
