from tabulaflow.app.tui.rendering import _format_table_cell, format_media_cell
from tabulaflow.app.tui.screens.results import CellBrowserScreen, DataBrowserScreen

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"\x00" * 32
AUDIO = b"ID3\x03\x00" + b"\x00" * 32


def test_binary_cell_uses_shared_media_detection() -> None:
    text, language = CellBrowserScreen._format_value({"bytes": PNG, "path": None})

    assert text.startswith("<image/png: 40 bytes>")
    assert language is None


def test_media_collection_has_concise_summary_across_tui_views() -> None:
    value = [PNG, None, PDF, AUDIO]
    expected = "<3 media items: 1 image, 1 PDF, 1 audio>"

    assert format_media_cell(value) == expected
    assert _format_table_cell(value) == expected
    assert DataBrowserScreen._format_cell(value).plain == expected
    assert CellBrowserScreen._format_value(value) == (expected, None)


def test_mixed_collection_summarizes_binary_leaves() -> None:
    value = [PNG, "caption"]

    assert format_media_cell(value) is None
    assert "[binary: 40 bytes]" in _format_table_cell(value)
    assert "\\x89PNG" not in _format_table_cell(value)
