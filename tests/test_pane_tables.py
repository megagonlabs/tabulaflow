"""Tests for media helpers and browser-pane table payloads."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from tabulaflow.app.media import sniff_binary, try_decode_base64
from tabulaflow.app.pane import (
    build_table_data,
)


PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 16
GIF_MAGIC = b"GIF89a" + b"\x00" * 16
WEBP_MAGIC = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8
WAV_MAGIC = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 8
BMP_MAGIC = b"BM" + b"\x00" * 30
TIFF_LE = b"II*\x00" + b"\x00" * 28
TIFF_BE = b"MM\x00*" + b"\x00" * 28
PDF_MAGIC = b"%PDF-1.4\n" + b"\x00" * 16
MP3_ID3 = b"ID3\x03\x00" + b"\x00" * 16
MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 16
OGG_MAGIC = b"OggS" + b"\x00" * 16
FLAC_MAGIC = b"fLaC" + b"\x00" * 16
MP4_MAGIC = b"\x00\x00\x00 ftypisom" + b"\x00" * 16
WEBM_MAGIC = b"\x1a\x45\xdf\xa3" + b"\x00" * 16
SVG_BYTES = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"


def _payload_rows(payload: dict[str, object]) -> list[dict[str, Any]]:
    dataset = cast(dict[str, Any], payload["dataset"])
    return cast(list[dict[str, Any]], dataset["rows"])


def _payload_table(payload: dict[str, object]) -> dict[str, Any]:
    return cast(dict[str, Any], payload["table"])


class TestSniffBinary:
    @pytest.mark.parametrize(
        "raw,expected_ext,expected_mime",
        [
            (PNG_MAGIC, ".png", "image/png"),
            (JPEG_MAGIC, ".jpg", "image/jpeg"),
            (GIF_MAGIC, ".gif", "image/gif"),
            (WEBP_MAGIC, ".webp", "image/webp"),
            (WAV_MAGIC, ".wav", "audio/wav"),
            (BMP_MAGIC, ".bmp", "image/bmp"),
            (TIFF_LE, ".tif", "image/tiff"),
            (TIFF_BE, ".tif", "image/tiff"),
            (PDF_MAGIC, ".pdf", "application/pdf"),
            (MP3_ID3, ".mp3", "audio/mpeg"),
            (MP3_FRAME, ".mp3", "audio/mpeg"),
            (OGG_MAGIC, ".ogg", "audio/ogg"),
            (FLAC_MAGIC, ".flac", "audio/flac"),
            (MP4_MAGIC, ".mp4", "video/mp4"),
            (WEBM_MAGIC, ".webm", "video/webm"),
            (SVG_BYTES, ".svg", "image/svg+xml"),
        ],
    )
    def test_known_magic(self, raw: bytes, expected_ext: str, expected_mime: str) -> None:
        assert sniff_binary(raw) == (expected_ext, expected_mime)

    def test_unknown_returns_none(self) -> None:
        assert sniff_binary(b"\x00\x01\x02\x03\x04\x05") is None

    def test_too_short(self) -> None:
        assert sniff_binary(b"\x89") is None


class TestTryDecodeBase64:
    def test_plain_base64(self) -> None:
        png_b64 = base64.b64encode(PNG_MAGIC).decode("ascii")
        # Pad to be long enough to clear the min-length gate.
        padded = png_b64 + "A" * max(0, 64 - len(png_b64))
        # Use exact base64 of a longer payload to avoid garbage padding.
        payload = base64.b64encode(PNG_MAGIC + b"\x00" * 64).decode("ascii")
        assert try_decode_base64(payload) is not None
        # And the short string path returns None.
        del padded

    def test_data_uri(self) -> None:
        png_b64 = base64.b64encode(PNG_MAGIC + b"\x00" * 64).decode("ascii")
        data_uri = f"data:image/png;base64,{png_b64}"
        decoded = try_decode_base64(data_uri)
        assert decoded is not None
        assert decoded.startswith(b"\x89PNG\r\n\x1a\n")

    def test_short_string_rejected(self) -> None:
        assert try_decode_base64("YWJj") is None  # "abc"

    def test_garbage_rejected(self) -> None:
        assert try_decode_base64("not base64 at all !!! " * 5) is None


class TestBuildTableData:
    def test_renders_image_column_inline(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"img": [PNG_MAGIC, PNG_MAGIC], "name": ["a", "b"]})
        payload = build_table_data(df, asset_stem="rec_abc", output_dir=tmp_path)

        rows = _payload_rows(payload)
        table = _payload_table(payload)
        assert rows[0]["c0"]["src"].startswith("data:image/png;base64,")
        assert table["columns"][0]["formatter"] == "media"
        assert not (tmp_path / "rec_abc").exists()

    def test_spills_large_blobs(self, tmp_path: Path) -> None:
        big_png = PNG_MAGIC + b"\x00" * (300 * 1024)
        df = pd.DataFrame({"img": [big_png]})
        payload = build_table_data(df, asset_stem="rec_xyz", output_dir=tmp_path, inline_cap=256 * 1024)

        sib_dir = tmp_path / "rec_xyz"
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
        payload = build_table_data(df, asset_stem="rec_hfimg", output_dir=tmp_path)

        rows = _payload_rows(payload)
        assert rows[0]["c0"]["src"].startswith("data:image/png;base64,")

    def test_base64_string_column_rendered(self, tmp_path: Path) -> None:
        png_b64 = base64.b64encode(PNG_MAGIC + b"\x00" * 64).decode("ascii")
        df = pd.DataFrame({"img_b64": [png_b64, png_b64]})
        payload = build_table_data(df, asset_stem="rec_b64", output_dir=tmp_path)

        rows = _payload_rows(payload)
        assert rows[0]["c0"]["src"].startswith("data:image/png;base64,")

    def test_row_cap_truncates(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"n": list(range(1000))})
        payload = build_table_data(df, asset_stem="rec_cap", output_dir=tmp_path, max_rows=10)

        table = _payload_table(payload)
        assert table["meta"] == "showing 10 of 1,000 rows · 1 column"
        assert table["truncatedRows"] == 990

    def test_max_height_is_preserved(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        payload = build_table_data(df, asset_stem="rec_short_pane", output_dir=tmp_path, max_height=640)

        assert _payload_table(payload)["maxHeight"] == 640

    def test_mixed_column_not_treated_as_media(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"col": [PNG_MAGIC, "plain string", 42, None, b"random"]})
        payload = build_table_data(df, asset_stem="rec_mix", output_dir=tmp_path)

        assert _payload_table(payload)["columns"][0]["formatter"] == "text"

    def test_numeric_column_gets_number_sorter(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        payload = build_table_data(df, asset_stem="rec_assets", output_dir=tmp_path)

        assert _payload_table(payload)["columns"][0]["sorter"] == "number"
