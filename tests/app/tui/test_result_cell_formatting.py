from tabulaflow.app.tui.screens.results import CellBrowserScreen

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def test_binary_cell_uses_shared_media_detection() -> None:
    text, language = CellBrowserScreen._format_value({"bytes": PNG, "path": None})

    assert text.startswith("<image/png: 40 bytes>")
    assert language is None
