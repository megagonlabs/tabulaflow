"""Tests for the cell/table dump helpers in tabulaflow.app.render."""

from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import pytest

from tabulaflow.app.render import (
    render_table_html,
    serialize_cell,
    sniff_binary,
    try_decode_base64,
    write_cell_dump,
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


class TestSerializeCell:
    def test_png_bytes_get_png_suffix(self) -> None:
        content, suffix = serialize_cell(PNG_MAGIC)
        assert isinstance(content, bytes)
        assert suffix == ".png"

    def test_unknown_bytes_get_bin_suffix(self) -> None:
        content, suffix = serialize_cell(b"\x00\x01\x02\x03randomgarbage")
        assert isinstance(content, bytes)
        assert suffix == ".bin"

    def test_base64_png_string_decoded(self) -> None:
        png_b64 = base64.b64encode(PNG_MAGIC + b"\x00" * 64).decode("ascii")
        content, suffix = serialize_cell(png_b64)
        assert isinstance(content, bytes)
        assert suffix == ".png"

    def test_data_uri_string_decoded(self) -> None:
        png_b64 = base64.b64encode(PNG_MAGIC + b"\x00" * 64).decode("ascii")
        content, suffix = serialize_cell(f"data:image/png;base64,{png_b64}")
        assert isinstance(content, bytes)
        assert suffix == ".png"

    def test_dict_serialized_as_json(self) -> None:
        content, suffix = serialize_cell({"a": 1, "b": [2, 3]})
        assert isinstance(content, str)
        assert suffix == ".json"
        assert '"a"' in content

    def test_sql_string_gets_sql_suffix(self) -> None:
        content, suffix = serialize_cell("SELECT * FROM t")
        assert content == "SELECT * FROM t"
        assert suffix == ".sql"

    def test_plain_string_gets_txt(self) -> None:
        content, suffix = serialize_cell("hello world")
        assert content == "hello world"
        assert suffix == ".txt"


class TestWriteCellDump:
    def test_writes_bytes_for_image(self, tmp_path: Path) -> None:
        path = write_cell_dump(PNG_MAGIC, tmp_path)
        assert path.suffix == ".png"
        assert path.read_bytes() == PNG_MAGIC

    def test_writes_text_for_string(self, tmp_path: Path) -> None:
        path = write_cell_dump("hello", tmp_path)
        assert path.suffix == ".txt"
        assert path.read_text() == "hello"


class TestRenderTableHtml:
    def test_renders_image_column_inline(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"img": [PNG_MAGIC, PNG_MAGIC], "name": ["a", "b"]})
        html_path = tmp_path / "T_abc.html"
        render_table_html(df, html_path)
        text = html_path.read_text()
        assert "<img" in text
        assert "data:image/png;base64," in text
        # No spill dir created when all blobs fit under cap.
        assert not (tmp_path / "T_abc").exists()

    def test_spills_large_blobs(self, tmp_path: Path) -> None:
        big_png = PNG_MAGIC + b"\x00" * (300 * 1024)
        df = pd.DataFrame({"img": [big_png]})
        html_path = tmp_path / "T_xyz.html"
        render_table_html(df, html_path, inline_cap=256 * 1024)
        text = html_path.read_text()
        sib_dir = tmp_path / "T_xyz"
        assert sib_dir.is_dir()
        spilled = list(sib_dir.glob("*.png"))
        assert len(spilled) == 1
        assert spilled[0].read_bytes() == big_png
        # HTML references the sibling file, not a data URI.
        assert f"./{sib_dir.name}/" in text
        assert "data:image/png;base64," not in text

    def test_hf_struct_image_column_rendered(self, tmp_path: Path) -> None:
        """DuckDB returns HF Image columns as ``{"bytes": <png>, "path": ...}`` dicts.

        Regression: the sniffer only handled raw bytes / base64 strings, so HF
        image columns (e.g. the CIFAR-10 cache) rendered as JSON text instead
        of inline images.
        """
        cell = {"bytes": PNG_MAGIC, "path": None}
        df = pd.DataFrame({"img": [cell, cell, cell], "label": [1, 2, 3]})
        html_path = tmp_path / "T_hfimg.html"
        render_table_html(df, html_path)
        text = html_path.read_text()
        assert "<img" in text
        assert "data:image/png;base64," in text

    def test_base64_string_column_rendered(self, tmp_path: Path) -> None:
        png_b64 = base64.b64encode(PNG_MAGIC + b"\x00" * 64).decode("ascii")
        df = pd.DataFrame({"img_b64": [png_b64, png_b64]})
        html_path = tmp_path / "T_b64.html"
        render_table_html(df, html_path)
        text = html_path.read_text()
        assert "<img" in text
        assert "data:image/png;base64," in text

    def test_row_cap_truncates(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"n": list(range(1000))})
        html_path = tmp_path / "T_cap.html"
        render_table_html(df, html_path, max_rows=10)
        text = html_path.read_text()
        # Truncation surfaces in the document title rather than the page body
        # (user wants only the table visible, no header chrome).
        assert "showing 10 of 1,000 rows" in text

    def test_mixed_column_not_treated_as_media(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"col": [PNG_MAGIC, "plain string", 42, None, b"random"]})
        html_path = tmp_path / "T_mix.html"
        render_table_html(df, html_path)
        text = html_path.read_text()
        # Only one PNG out of 5 entries; should not trigger the column renderer.
        # The HTML still contains "<img" inside Tabulator's bundled JS source
        # (img-loading helper), so check the row data instead: there should
        # be no _display field (which the media renderer emits).
        assert '"col_display"' not in text

    def test_tabulator_assets_inlined(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        html_path = tmp_path / "T_assets.html"
        render_table_html(df, html_path)
        text = html_path.read_text()
        # Tabulator JS is inlined (single-file, offline).
        assert "Tabulator" in text
        # Modal markup is present.
        assert 'id="modal"' in text
        # Numeric column gets a number sorter.
        assert '"sorter": "number"' in text or '"sorter":"number"' in text
